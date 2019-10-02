import argparse
import collections
import hashlib
import jinja2
import json
import logging
import os
import re
import subprocess
import sys
import time
import yaml

from enum import IntFlag

script_dir = os.path.dirname(os.path.realpath(__file__))

from buildtools import os_utils, log

"""
Usage:
    $ python create.py voxwords.txt

Requires festival, sox, and vorbis-tools.

create.py - Uses festival to generate word oggs.

Copyright 2013-2019 Rob "N3X15" Nelson <nexis@7chan.org>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

###############################################
# CONFIG
###############################################

CODEBASE = 'vg'

# Voice you want to use
# VOICE='rab_diphone'
# This is the nitech-made ARCTIC voice, tut on how to install:
# http://ubuntuforums.org/showthread.php?t=751169 ("Installing the enhanced Nitech HTS voices" section)
# VOICE='nitech_us_bdl_arctic_hts'
# VOICE='nitech_us_jmk_arctic_hts'
# VOICE='nitech_us_awb_arctic_hts'
VOICE = 'nitech_us_slt_arctic_hts'  # less bored US female
# VOICE='nitech_us_clb_arctic_hts' # DEFAULT, bored US female (occasionally comes up with british pronunciations?!)
# VOICE='nitech_us_rms_arctic_hts'

# PHONESET='mrpa'
PHONESET = ''

MALE = False
# What we do with SoX:
if MALE:
    VOICE = 'nitech_us_slt_arctic_hts'  # less bored US female
    # VOICE='cmu_us_slt_arctic_hts'
    SOX_ARGS = 'pitch -500'
    SOX_ARGS += ' stretch 1.2'  # Starts the gravelly sound, lowers pitch a bit.
    SOX_ARGS += ' synth sine amod 60'
    SOX_ARGS += ' chorus 0.7 0.9 55 0.4 0.25 2 -t'
    SOX_ARGS += ' phaser 0.9 0.85 4 0.23 1.3 -s'
else:
    VOICE = 'nitech_us_clb_arctic_hts'  # DEFAULT, bored US female (occasionally comes up with british pronunciations?!)
    SOX_ARGS = 'stretch 1.1'
    SOX_ARGS += ' chorus 0.7 0.9 55 0.4 0.25 2 -t'
    SOX_ARGS += ' phaser 0.9 0.85 4 0.23 1.3 -s'
SOX_ARGS += ' bass -40'
SOX_ARGS += ' highpass 22 highpass 22'
SOX_ARGS += ' compand 0.01,1 -90,-90,-70,-70,-60,-20,0,0 -5 -20'  # Dynamic range compression.
# SOX_ARGS += ' echos 0.8 0.5 100 0.25 10 0.25' # Good with stretch, otherwise sounds like bees.
SOX_ARGS += ' echos 0.3 0.5 100 0.25 10 0.25'  # Good with stretch, otherwise sounds like bees.
#SOX_ARGS += ' delay 0.5'
SOX_ARGS += ' norm'

RECOMPRESS_ARGS = ['-c:a', 'libvorbis', '-ac', '1', '-ar', '16000', '-q:a', '0', '-speed', '0', '-threads', '8', '-y']

# Have to do the trimming seperately.
PRE_SOX_ARGS = 'trim 0 -0.1'  # Trim off last 0.2s.

# Shit we shouldn't change or overwrite. (Boops, pauses, etc)
preexisting = {
    '.': 1,
    ',': 1,
    'bloop': 1,
    'bizwarn': 1,  # Is this a misspelling of the below?
    'buzwarn': 1,
    'doop': 1,
    'dadeda': 1,
    'woop': 1,
}

################################################
# ROB'S AWFUL CODE BELOW (cleanup planned)
################################################

REGEX_SEARCH_STRINGS = re.compile(r'(\'|")(.*?)(?:\1)')

othersounds = []
known_phonemes = {}
wordlist = dict(preexisting.items())
ALL_WORDS={}
args = None


def md5sum(filename):
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()

class EWordFlags(IntFlag):
    NONE    = 0
    OLD_VOX = 1 # AKA preexisting
    SFX     = 2

class Word(object):
    def __init__(self, word: str, wordlen: int):
        self.id: str = word
        self.wordlen: int = wordlen
        self.phrase: str = ''
        self.filename: str = ''
        self.flags: EWordFlags = EWordFlags.NONE

    def serialize(self) -> dict:
        return {
            'wordlen': self.wordlen,
            'filename': self.filename,
            'flags': [x.name.lower().replace('_','-') for x in list(EWordFlags) if x.value > 0 and (self.flags & x) == x]
        }

class Pronunciation(object):
    '''
    Festival can fuck up pronunciation of stuff, but thankfully, we can specify a new set.

    Unfortunately, it's in LISP, which this class will generate for you.
    '''
    def __init__(self):
        self.syllables = []
        self.name = []
        self.type = 'n'
        self.phoneConv = {
            'mrpa': {
                'ae': 'a',
                'ih': 'i',
            }
        }
        # DMU phonemes + pau
        self.validPhonemes = [
            'aa',
            'ae',
            'ah',
            'ao',
            'aw',
            'ay',
            'b',
            'ch',
            'd',
            'dh',
            'eh',
            'er',
            'ey',
            'f',
            'g',
            'hh',
            'ih',
            'iy',
            'jh',
            'k',
            'l',
            'm',
            'n',
            'ng',
            'ow',
            'oy',
            'p',
            'r',
            's',
            'sh',
            't',
            'th',
            'uh',
            'uw',
            'v',
            'w',
            'y',
            'z',
            'zh',
            'pau']
    """
    ( "walkers" n ((( w oo ) 1) (( k @ z ) 0)) )
    ( "present" v ((( p r e ) 0) (( z @ n t ) 1)) )
    ( "monument" n ((( m o ) 1) (( n y u ) 0) (( m @ n t ) 0)) )
    """

    def toLisp(self):
        lispSyllables = []
        for syllable in self.syllables:
            lispSyllables.append('( ( {0} ) {1} )'.format(' '.join(syllable[0]), syllable[1]))
        return '(lex.add.entry\n\t\'( "{0}" {1} ( {2} ) ))\n'.format(self.name, self.type[0], ' '.join(lispSyllables))

    """
    walkers: noun "w oo" 'k @ z'
    present: verb 'p r e' "z @ n t"
    monument: noun "mo" 'n y u' 'm @ n t'
    """

    def parseWord(self, line):
        global REGEX_SEARCH_STRINGS
        lineChunks = line.split(' ')
        self.name = lineChunks[0].strip(':')
        self.type = lineChunks[1].strip()
        pronunciation = ' '.join(lineChunks[2:])
        for match in REGEX_SEARCH_STRINGS.finditer(pronunciation):
            stressLevel = 0
            if match.group(1) == '"':
                stressLevel = 1
            phonemes = []
            for phoneme in match.group(2).split(' '):
                if phoneme not in self.validPhonemes:
                    log.error('INVALID PHONEME "{0}" IN LEX ENTRY "{1}"'.format(phoneme, self.name))
                    sys.exit(1)
                if PHONESET in self.phoneConv:
                    phoneset = self.phoneConv[PHONESET]
                    if phoneme in phoneset:
                        phoneme = phoneset[phoneme]
                phonemes += [phoneme]
            self.syllables += [(phonemes, stressLevel)]
        log.info('Parsed {0} as {1}.'.format(pronunciation, repr(self.syllables)))



def GenerateForWord(word, wordfile):
    global wordlist, preexisting, SOX_ARGS, known_phonemes, othersounds
    my_phonemes = {}
    if wordfile in preexisting:
        log.info('Skipping {0}.ogg (Marked as PRE_EXISTING)'.format(wordfile))
        return
    if '/' not in wordfile:
        wordlist[wordfile] = len(word.split(' '))
    else:
        othersounds += [wordfile]
    md5 = hashlib.md5(word.encode('utf-8')).hexdigest()
    for w in word.split(' '):
        w = w.lower()
        if w in known_phonemes:
            my_phonemes[w] = known_phonemes[w].toLisp().replace('\n', '')
    md5 += '\n'.join(my_phonemes.values())
    md5 += SOX_ARGS + PRE_SOX_ARGS
    md5 += VOICE
    oggfile = os.path.abspath(os.path.join('dist', 'sound', 'vox_fem', wordfile + '.ogg'))
    if '/' in wordfile:
        oggfile = os.path.abspath(os.path.join('dist', wordfile + '.ogg'))
    cachefile = os.path.abspath(os.path.join('cache', wordfile.replace(os.sep, '_').replace('.', '') + '.dat'))

    parent = os.path.dirname(oggfile)
    if not os.path.isdir(parent):
        os.makedirs(parent)

    parent = os.path.dirname(cachefile)
    if not os.path.isdir(parent):
        os.makedirs(parent)

    if os.path.isfile(oggfile):
        old_md5 = ''
        if os.path.isfile(cachefile):
            with open(cachefile, 'r') as md5f:
                old_md5 = md5f.read()
        if old_md5 == md5:
            log.info('Skipping {0}.ogg (exists)'.format(wordfile))
            return
    log.info('Generating {0}.ogg ({1})'.format(wordfile, repr(word)))
    text2wave = None
    if word.startswith('@'):
        text2wave = 'ffmpeg -i '+word[1:]+' tmp/VOX-word.wav'
    else:
        with open('tmp/VOX-word.txt', 'w') as wf:
            wf.write(word)

        text2wave = 'text2wave tmp/VOX-word.txt -o tmp/VOX-word.wav'
        if os.path.isfile('tmp/VOXdict.lisp'):
            text2wave = 'text2wave -eval tmp/VOXdict.lisp tmp/VOX-word.txt -o tmp/VOX-word.wav'
    with open(cachefile, 'w') as wf:
        wf.write(md5)
    for fn in ('tmp/VOX-word.wav', 'tmp/VOX-soxpre-word.wav', 'tmp/VOX-sox-word.wav'):
        if os.path.isfile(fn):
            os.remove(fn)
    cmds = []
    cmds += [(text2wave.split(' '), 'tmp/VOX-word.wav')]
    cmds += [(['sox', 'tmp/VOX-word.wav', 'tmp/VOX-soxpre-word.wav'] + PRE_SOX_ARGS.split(' '), 'tmp/VOX-soxpre-word.wav')]
    cmds += [(['sox', 'tmp/VOX-soxpre-word.wav', 'tmp/VOX-sox-word.wav'] + SOX_ARGS.split(' '), 'tmp/VOX-sox-word.wav')]
    cmds += [(['oggenc', 'tmp/VOX-sox-word.wav', '-o', 'tmp/VOX-encoded.ogg'], 'tmp/VOX-encoded.ogg')]
    cmds += [(['ffmpeg', '-i', 'tmp/VOX-encoded.ogg']+RECOMPRESS_ARGS+[oggfile], oggfile)]
    for command_spec in cmds:
        (command, cfn) = command_spec
        with os_utils.TimeExecution(command[0]):
            os_utils.cmd(command, echo=False, critical=True, show_output=False)
    for command_spec in cmds:
        (command, cfn) = command_spec
        if not os.path.isfile(fn):
            log.error("File '{0}' doesn't exist, command '{1}' probably failed!".format(cfn, command))
            sys.exit(1)


def ProcessWordList(filename):
    toprocess = {}
    with open(filename, 'r') as words:
        for line in words:
            if line.startswith("#"):
                continue
            if line.strip() == '':
                continue
            if '=' in line:
                (wordfile, phrase) = line.split('=')
                toprocess[wordfile.strip()] = phrase.strip()
            elif line != '' and ' ' not in line and len(line) > 0:
                word = line.strip()
                toprocess[word] = word
    for wordfile, phrase in iter(sorted(toprocess.items())):
        GenerateForWord(phrase, wordfile)
        ALL_WORDS[wordfile] = phrase


def ProcessLexicon(filename):
    global known_phonemes, VOICE
    with open('tmp/VOXdict.lisp', 'w') as lisp:
        if VOICE != '':
            lisp.write('(voice_{0})\n'.format(VOICE))
        with open(filename, 'r') as lines:
            for line in lines:
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    p = Pronunciation()
                    p.parseWord(line)
                    lisp.write(p.toLisp())
                    known_phonemes[p.name] = p


if not os.path.isdir('tmp'):
    os.makedirs('tmp')
DIST_DIR = 'dist'
CODE_DIR = ''
vox_sounds_path = ''
templatefile = ''
PREEX_SOUND = 'sound/vox/{}.wav'
NUVOX_SOUND = 'sound/vox_fem/{}.ogg'
if CODEBASE == 'tg':
    CODE_DIR = os.path.join(DIST_DIR, 'code', 'modules', 'mob', 'living', 'silicon', 'ai')
    vox_sounds_path = os.path.join(CODE_DIR, 'vox_sounds.dm')
    templatefile = 'tglist.jinja'
else:
    CODE_DIR = os.path.join(DIST_DIR, 'code', 'defines')
    vox_sounds_path = os.path.join(CODE_DIR, 'vox_sounds.dm')
    templatefile = 'vglist.jinja'

DATA_DIR = os.path.join(DIST_DIR, 'data')
os_utils.ensureDirExists(CODE_DIR)
os_utils.ensureDirExists(DATA_DIR)
ProcessLexicon('lexicon.txt')
for arg in sys.argv[1:]:
    ProcessWordList(arg)
soundsToKeep = set()
for sound in othersounds:
    soundsToKeep.add(os.path.join(DIST_DIR, sound + '.ogg'))

wordobjs = collections.OrderedDict()
for word, wordlen in sorted(wordlist.items()):
    # If it has a path, it's being manually specified.
    if '/' in word:
        continue
    w = Word(word, wordlen)
    w.filename = NUVOX_SOUND.format(word)
    if word in preexisting:
        w.flags |= EWordFlags.OLD_VOX
        w.filename = PREEX_SOUND.format(word)
    if word in ALL_WORDS:
        # We should always drop in here, but additional checks are always good.
        w.phrase = ALL_WORDS[word].strip()
        if w.phrase.startswith('@'):
            w.flags |= EWordFlags.SFX
    wordobjs[word] = w
    soundsToKeep.add(os.path.join(DIST_DIR, w.filename))

jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(['./templates']))
templ = jenv.get_template(templatefile)
os_utils.ensureDirExists(os.path.dirname(vox_sounds_path))
with open(vox_sounds_path, 'w') as f:
    f.write(templ.render(WORDS=wordobjs.values()))
soundsToKeep.add(vox_sounds_path)

os_utils.ensureDirExists(DATA_DIR)
with open(os.path.join(DATA_DIR, 'vox_data.json'), 'w') as f:
    data = {
        'version': 1,
        'compiled': time.time(),
        'voice': VOICE,
        'phoneset': PHONESET,
        #'preexisting': preexisting,
        #'phonemes': known_phonemes,
        'words': collections.OrderedDict({w.id: w.serialize() for w in wordobjs.values() if '/' not in w.id}),
    }
    json.dump(data, f, indent=2)
soundsToKeep.add(os.path.join(DATA_DIR, 'vox_data.json'))
for root, dirs, files in os.walk('dist/', topdown=False):
    for name in files:
        filename = os.path.join(root, name)
        if filename not in soundsToKeep:
            log.warning('Removing {0} (no longer defined)'.format(filename))
            os.remove(filename)

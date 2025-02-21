import sys
import os

import logging
import argparse
import multiprocessing

from yaml import safe_load
from yaml import YAMLError

from ss13vox.voice import EVoiceSex

# from ss13vox.voice import SFXVoice
from ss13vox.voice import VoiceRegistry

FORMAT = "%(levelname)s --- %(message)s"
# LOGLEVEL = logging.INFO
LOGLEVEL = logging.DEBUG

logging.basicConfig(format=FORMAT, level=LOGLEVEL)
logger = logging.getLogger("AB Main")

TEMP_DIR = "tmp"
DIST_DIR = "dist"
DATA_DIR = os.path.join(DIST_DIR, "data")
voices = []
vox_sounds_path = ""
configFile = "config.yml"
pathConfigFile = "paths.yml"


def loadYaml(filename):
    try:
        with open(filename) as stream:
            try:
                parsed_yaml = safe_load(stream)
                config = parsed_yaml
            except YAMLError:
                logger.error(f"Invalid config in {filename}")
                sys.exit(15)
    except OSError:
        logger.error(f"File not found: {filename}")
        sys.exit(10)
    return config


def main(args):
    logger.info("Started voice generation")
    for _k, _v in args.items():
        logger.debug(f"Using argument {_k}={_v}")
    logger.debug(
        f"Paths:\n  temporary folder = {TEMP_DIR}\n"
        f"  distribution folder = {DIST_DIR}\n"
        f"  voices = {voices}\n"
    )

    # get config
    config = loadYaml(args["config"])

    # configure
    # station = args["station"]
    # preexSound = config["paths"][station]["sound"]["old-vox"]
    # nuvoxSound = config["paths"][station]["sound"]["new-vox"]
    # vox_sounds_path = config["paths"][station]["vox_sounds"]["path"]
    # templatefile = config["paths"][station]["vox_sounds"]["template"]
    # vox_data_path = config["paths"][station]["vox_data"]

    voice_assignments = {}
    all_voices = []
    # default_voice: Voice = VoiceRegistry.Get(USSLTFemale.ID)
    # This should default to config['voices']['default']
    # sfx_voice: SFXVoice = SFXVoice()
    configured_voices: dict[str, dict] = {}

    for sexID, voiceid in config["voices"].items():
        voice = VoiceRegistry.Get(voiceid)
        assert sexID != ""
        voice.assigned_sex = sexID
        if sexID in ("fem", "mas"):
            sex = EVoiceSex(sexID)
            assert voice.SEX == sex
            voices.append(voice)
        elif sexID == "default":
            pass
            # default_voice = voice
        voice_assignments[voice.assigned_sex] = []
        all_voices.append(voice)
        configured_voices[sexID] = voice.serialize()

    logger.debug(f"List of all voices found: {all_voices}")
    logger.debug(f"List of all voices configured: {configured_voices}")

    # voice_assignments[sfx_voice.assigned_sex] = []
    # all_voices += [sfx_voice]
    # configured_voices[sfx_voice.assigned_sex] = sfx_voice.serialize()

    # os_utils.ensureDirExists(DATA_DIR)
    # with log.info("Parsing lexicon..."):
    #     lexicon = ParseLexiconText("lexicon.txt")

    # phrases = []
    # phrasesByID = {}
    # broked = False
    # max_wordlen = config.get("max-wordlen", 30)
    # for filename in config.get(
    #     "phrasefiles", ["announcements.txt", "voxwords.txt"]
    # ):
    #     for p in ParsePhraseListFrom(filename):
    #         p.wordlen = min(max_wordlen, p.wordlen)
    #         if p.id in phrasesByID:
    #             duplicated = phrasesByID[p.id]
    #             log.critical(
    #                 f"Duplicate phrase with ID {p.id} "
    #                 f"in file {p.deffile} on line {p.defline}! "
    #                 f"First instance in file {duplicated.deffile} "
    #                 f"on line {duplicated.defline}."
    #             )
    #             broked = True
    #             continue
    #         phrases += [p]
    #         phrasesByID[p.id] = p
    #     if broked:
    #         sys.exit(1)

    # soundsToKeep = set()
    # for sound in OTHERSOUNDS:
    #     soundsToKeep.add(os.path.join(DIST_DIR, sound + ".ogg"))

    # phrases.sort(key=lambda x: x.id)

    # overrides = config.get("overrides", {})
    # for phrase in phrases:
    #     if phrase.id in overrides:
    #         phrase.fromOverrides(overrides.get(phrase.id))
    #     phrase_voices = list(voices)
    #     # If it has a path, it's being manually specified.
    #     if "/" in phrase.id:
    #         phrase.filename = phrase.id + ".ogg"
    #         phrase_voices = [default_voice]
    #         soundsToKeep.add(
    #             os.path.abspath(os.path.join(DIST_DIR, phrase.filename))
    #         )
    #     else:
    #         phrase.filename = "" + nuvoxSound
    #         if phrase.hasFlag(EPhraseFlags.OLD_VOX):
    #             phrase_voices = [default_voice]
    #             phrase.filename = preexSound.format(ID=phrase.id)
    #             for voice in ["fem", "mas"]:
    #                 phrase.files[voice] = FileData()
    #                 phrase.files[voice].filename = phrase.filename
    #                 phrase.files[voice].checksum = ""
    #                 phrase.files[voice].duration = (
    #                     phrase.override_duration or -1
    #                 )
    #                 phrase.files[voice].size = phrase.override_size or -1
    #                 # voice_assignments[voice].append(phrase)
    #             soundsToKeep.add(
    #                 os.path.abspath(os.path.join(DIST_DIR, phrase.filename))
    #             )
    #             continue

    #     if phrase.hasFlag(EPhraseFlags.SFX):
    #         phrase_voices = [sfx_voice]

    #     if not phrase.hasFlag(EPhraseFlags.OLD_VOX):
    #         log.info(
    #             "%s - %r", phrase.id, [x.assigned_sex for x in phrase_voices]
    #         )
    #         for v in phrase_voices:
    #             voice_assignments[v.assigned_sex].append(phrase)
    #             # phrase.files[v.assigned_sex] = fd
    # sys.exit(1)
    # for voice in all_voices:
    #     print(voice.ID, voice.assigned_sex)
    #     DumpLexiconScript(
    #         voice.FESTIVAL_VOICE_ID, lexicon.values(), "tmp/VOXdict.lisp"
    #     )
    #     for phrase in voice_assignments[voice.assigned_sex]:
    #         GenerateForWord(phrase, voice, soundsToKeep, args)
    #         sexes = set()
    #         for vk, fd in phrase.files.items():
    #             soundsToKeep.add(
    #                 os.path.abspath(os.path.join(DIST_DIR, fd.filename))
    #             )

    # jenv = jinja2.Environment(
    #     loader=jinja2.FileSystemLoader(["./templates"])
    # )
    # jenv.add_extension("jinja2.ext.do")  # {% do ... %}
    # templ = jenv.get_template(templatefile)
    # with log.info("Writing sound list to %s...", vox_sounds_path):
    #     os_utils.ensureDirExists(os.path.dirname(vox_sounds_path))
    #     assetcache = {}
    #     sound2id = {}
    #     with open(vox_sounds_path, "w") as f:
    #         sexes = {
    #             "fem": [],
    #             "mas": [],
    #             "default": [],
    #             # 'sfx': [],
    #         }
    #         for p in phrases:
    #             for k in p.files.keys():
    #                 assetcache[p.getAssetKey(k)] = p.files[k].filename
    #                 sound2id[p.files[k].filename] = p.getAssetKey(k)
    #             if p.hasFlag(EPhraseFlags.NOT_VOX):
    #                 continue
    #             for k in p.files.keys():
    #                 if p.hasFlag(EPhraseFlags.SFX):
    #                     for sid in ("fem", "mas"):
    #                         if p not in sexes[sid]:
    #                             sexes[sid].append(p)
    #                 else:
    #                     sexes[k].append(p)
    #         f.write(
    #             templ.render(
    #                 InitClass=InitClass,
    #                 SEXES=sexes,
    #                 ASSETCACHE=assetcache,
    #                 SOUND2ID=sound2id,
    #                 PHRASES=[
    #                     p
    #                     for p in phrases
    #                     if not p.hasFlag(EPhraseFlags.NOT_VOX)
    #                 ],
    #             )
    #         )
    # soundsToKeep.add(os.path.abspath(vox_sounds_path))

    # os_utils.ensureDirExists(DATA_DIR)
    # with open(os.path.join(DATA_DIR, "vox_data.json"), "w") as f:
    #     data = {
    #         "version": 2,
    #         "compiled": time.time(),
    #         "voices": configured_voices,
    #         "words": collections.OrderedDict(
    #             {w.id: w.serialize() for w in phrases if "/" not in w.id}
    #         ),
    #     }
    #     json.dump(data, f, indent=2)
    # soundsToKeep.add(
    #     os.path.abspath(os.path.join(DATA_DIR, "vox_data.json"))
    # )

    # with open("tmp/written.txt", "w") as f:
    #     for filename in sorted(soundsToKeep):
    #         f.write(f"{filename}\n")

    # for root, _, files in os.walk(DIST_DIR, topdown=False):
    #     for name in files:
    #         filename = os.path.abspath(os.path.join(root, name))
    #         if filename not in soundsToKeep:
    #             log.warning(
    #                 "Removing {0} (no longer defined)".format(filename)
    #             )
    #             os.remove(filename)

    ####


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generation script for ss13-vox."
    )
    parser.add_argument(
        "--threads",
        "-j",
        type=int,
        default=multiprocessing.cpu_count(),
        help="How many threads to use in ffmpeg.",
    )
    parser.add_argument(
        "--echo",
        "-e",
        action="store_true",
        default=False,
        help="Echo external commands to console.",
    )
    parser.add_argument(
        "--station",
        "-s",
        type=str,
        default="vg",
        help="The station, defaults to 'vg'.",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="abconfig.yml",
        help="The configuration file to use, defaults to 'abconfig.yml",
    )
    args = vars(parser.parse_args())  # I prefer dictionaries

    main(args)

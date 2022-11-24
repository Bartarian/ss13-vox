import sys
from os.path import exists
import argparse
import multiprocessing
import logging
from yaml import YAMLError, safe_load

from ss13vox.voice import VoiceRegistry
from ss13vox.voice import EVoiceSex
from ss13vox.voice import SFXVoice
from ss13vox.voice import USSLTFemale
from ss13vox.voice import Voice

FORMAT = "%(levelname)s --- %(message)s"
#LOGLEVEL = logging.INFO
LOGLEVEL = logging.DEBUG

logging.basicConfig(format=FORMAT, level=LOGLEVEL)
logger=logging.getLogger("AB Main")

TEMP_DIR = "tmp"
DIST_DIR = "dist"
PREEX_SOUND = "sound/vox/{ID}.wav"
NUVOX_SOUND = "sound/vox_{SEX}/{ID}.wav"
voices = []
vox_sounds_path = ""
templatefile = ""
configFile = "config.yml"
pathConfigFile = "paths.yml"


def loadYaml(filename):
    try:
        with open(filename, 'r') as stream:
            try:
                parsed_yaml=safe_load(stream)
                config = parsed_yaml
            except YAMLError as exc:
                logger.error(f"Invalid config in {filename}")
                sys.exit(15)
    except OSError:
        logger.error(f"Invalid config in {filename}")
        sys.exit(10)
    except FileExistsError:
        logger.error(f"File {filename} already opened by another process.")
        sys.exit(12)
    return config


def main(args):
    logger.info("Started voice generation")
    logger.debug(f"Arguments:\n  threads = {args.threads}\n  echo = {args.echo}")
    logger.debug(
        f"Paths:\n  temporary folder = {TEMP_DIR}\n"
        f"  distribution folder = {DIST_DIR}\n"
        f"  PREEX_SOUND = {PREEX_SOUND}\n"
        f"  NUVOX_SOUND = {NUVOX_SOUND}\n"
        f"  voices = {voices}\n"
        f"  vox_sounds_path = {vox_sounds_path}\n"
        f"  templatefile = {templatefile}"
    )

    # get config
    config = loadYaml(configFile)
    pathconfig = loadYaml(pathConfigFile)

    PREEX_SOUN = pathconfig['vg']['sound']['old-vox']
    print(PREEX_SOUN)

    voice_assignments = {}
    all_voices = []
    default_voice: Voice = VoiceRegistry.Get(USSLTFemale.ID)    
    sfx_voice: SFXVoice = SFXVoice()
    configured_voices: dict[str, dict] = {}

    for sexID, voiceid in config['voices'].items():
        voice = VoiceRegistry.Get(voiceid)
        assert sexID != ''
        voice.assigned_sex = sexID
        if sexID in ('fem', 'mas'):
            sex = EVoiceSex(sexID)
            assert voice.SEX == sex
            voices.append(voice)
        elif sexID == 'default':
            default_voice = voice
        voice_assignments[voice.assigned_sex] = []
        all_voices.append(voice)
        configured_voices[sexID] = voice.serialize()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Generation script for ss13-vox.")
    parser.add_argument(
        "--threads", "-j", type=int, default=multiprocessing.cpu_count(),
        help="How many threads to use in ffmpeg.",
    )
    parser.add_argument(
        "--echo", "-e", action="store_true",
        default=False, help="Echo external commands to console.",
    )
    args = parser.parse_args()

    main(args)


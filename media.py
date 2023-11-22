import ffmpeg   # https://github.com/kkroening/ffmpeg-python
import logging
import pymkv    # https://github.com/sheldonkwoodward/pymkv
import re

from mediaexceptions import InvalidChannelCount, InvalidFilenameFormat
from pymediainfo import MediaInfo # https://pymediainfo.readthedocs.io/en/stable/

BITRATES = {
    2: "192K",
    6: "448K",
    8: "640K",
}

class Encoder():
    def __init__(self, mediaFile: str):
        self.input = mediaFile
        self.cmax  = 0
        self.cidx  = -1

        logging.basicConfig(
            format='%(asctime)s - %(message)s', 
            datefmt='%d-%b-%y %H:%M:%S', 
            level=logging.DEBUG,
        )

        # Parse the media for info
        self.parseMediaInfo()

        # Parse the file name
        self.parseFilename()
    
    def __str__(self):
        return str(self.info.to_json())
    
    def copy(self) -> None:
        logging.info(f'Starting copy of "{self.input}" to "{self.output} Copy.mkv"')
        out = ffmpeg.input(self.input).output(
            f'{self.output} Copy.mkv', 
            acodec='copy', 
            vcodec='copy',
        )

        logging.debug(out.get_args())
        out.run(overwrite_output=True)
        logging.info("Copy completed")
    
    def encode(self) -> None:
        match self.cmax:
            case 2:
                self.encodeStereo()
            case 6|8:
                self.encodeSurround()
            case _:
                raise InvalidChannelCount(f'Unexpected channel count: {self.cmax}')

    def encodeStereo(self) -> None:
        logging.info("Encoding stereo sound")
        
        outputFile = f'{self.output} Stereo.mkv'
        input = ffmpeg.input(self.input)
        out = ffmpeg.output(
            input['v'],
            input['a'],
            input['s?'],
            outputFile,
            **{
                "c:v": "copy",
                "c:s": "copy",
                "filter:a": "volume=2.0",
                "c:a:0": "libfdk_aac",
                "b:a:0": self.audio_bitrate,
                "metadata:s:a:0": "title=Stereo",
                "metadata": f'title="{self.output}"',
            }
        )
        
        logging.debug(out.get_args())
        out.run(overwrite_output=True)
        logging.info('Stereo encode complete')
        
        self.muxFile(outputFile)

    def encodeSurround(self) -> None:
        logging.debug("Encoding surround sound")
        
        outputFile = f'{self.output} Surround.mkv'
        input = ffmpeg.input(self.input)
        out = ffmpeg.output(
            input['v:0'], 
            input['a:0'], 
            input['a:0'],
            input['s?'],
            outputFile,
            **{
                "filter:a": "volume=2.0",
                "c:v": "copy", 
                "c:s": "copy",
                "c:a:0": "libfdk_aac", "b:a:0": self.audio_bitrate, "metadata:s:a:0": "title=Surround",
                "c:a:1": "libfdk_aac", "b:a:1": "192K", "ac:a:1": "2", "metadata:s:a:1": "title=Stereo",
                "metadata": f'title="{self.output}"',
            }
        )

        logging.debug(out.get_args())
        out.run(overwrite_output=True)
        logging.info('Surround sound encoding complete')

        self.muxFile(outputFile)
    
    def muxFile(self, input) -> None:
        logging.info(f'Starting mux of "{input}"')
        
        output = f'{self.output}.mkv'
        pymkv.MKVFile(input).mux(output)
        
        logging.info(f'Muxing complete for "{output}"')

    def parseFilename(self) -> None:
        logging.info(f'Parsing filename: {self.input}')
        
        # Determine the pattern for regex groupings
        logging.info(f'Extracting fields from filename')
        pattern = self.getPattern(self.input)
        match = re.match(pattern, self.input)
        
        if not match:
            raise InvalidFilenameFormat("Filename format is invalid")
        
        else:
            logging.debug(f'Found {len(match.groups())} fields')
            
            if len(match.groups()) > 3:
                # TV Show
                self.title     = match.group(1)
                self.season    = match.group(2)
                self.episode   = match.group(3)
                self.year      = match.group(4)
                self.extension = match.group(5)

                self.output = f'{self.title} - {self.season} - {self.episode} ({self.year})'
            else:
                # Movie
                self.title     = match.group(1)
                self.year      = match.group(2)
                self.extension = match.group(3)

                self.output = f'{self.title} ({self.year})'
            
            logging.info(f'Setting output field to "{self.output}"')
    
    def parseMediaInfo(self) -> None:
        logging.info(f'Parsing media info for "{self.input}"')
        self.info = MediaInfo.parse(self.input)

        # Determine max audio channel (2, 6, 8)
        for track in self.info.tracks:
            match track.track_type:
                case "Audio":
                    if track.channel_s > self.cmax:
                        self.cmax = track.channel_s
                        self.cidx += 1
        
        logging.info(f'Channel Max: {self.cmax}')

        # Determine audio bitrate, raise an exception if its not 2, 6, or 8
        try:
            self.audio_bitrate = BITRATES[self.cmax]
            logging.info(f'Setting audio bitrate to {self.audio_bitrate}')

        except:
            raise InvalidChannelCount(f'Unexpected channel count: {self.cmax}')

    # The filename format hints to the type of file we're working with:
    #   Movie: 'Title (Year) Orig'
    #   TV Show: 'Title - Marker - Episode (Year)'
    def getPattern(self, fileName:str) -> str:
        # The filename format hints to the type of file we're working with:
        #   Movie: 'Title (Year) Orig'
        #   TV Show: 'Title - Marker - Episode (Year)'
        if (len(fileName.split(' - '))) >= 3:
            logging.info(f'{fileName} appears to be a TV show')
            return re.compile(r'''
                ([a-zA-Z0-9\s]+)    # Title
                \s-\s               # Separator
                (\w+)               # Season/Episode Marker
                \s-\s               # Separator
                ([a-zA-Z0-9\s]+)    # Episode
                \s\(([0-9]+)\)      # Year
                \sOrig\.([mpkv4]+)  # Extension
            ''', re.VERBOSE)

        else:
            logging.info(f'{fileName} appears to be a movie')
            return re.compile(r'''
                ([a-zA-Z0-9\s\-]+)    # Title
                \s\(([0-9]+)\)      # Year
                \sOrig\.([mpkv4]+)  # Extension
            ''', re.VERBOSE)

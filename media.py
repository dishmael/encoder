import ffmpeg   # https://github.com/kkroening/ffmpeg-python
import logging
import pymkv    # https://github.com/sheldonkwoodward/pymkv
import re

from mediaexceptions import InvalidChannelCount, InvalidFilenameFormat
from pymediainfo import MediaInfo # https://pymediainfo.readthedocs.io/en/stable/

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
        logging.debug(f'Starting copy of "{self.input}" to "{self.output} Copy.mkv"')
        out = ffmpeg.input(self.input).output(
            f'{self.output} Copy.mkv', 
            acodec='copy', 
            vcodec='copy',
        )

        logging.debug(out.get_args())
        out.run(overwrite_output=True)
        logging.debug("Copy completed")
    
    def encode(self) -> None:
        match self.cmax:
            case 2:
                self.encodeStereo()
            case 6|8:
                self.encodeSurround()
            case _:
                raise InvalidChannelCount(f'Unexpected channel count: {self.cmax}')

    def encodeStereo(self) -> None:
        logging.debug("Encoding stereo sound")
        
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
                "c:v": "copy", 
                "c:s": "copy",
                "filter:a:0": "volume=2.0",
                "filter:a:1": "volume=2.0",
                "c:a:0": "libfdk_aac", "b:a:0": self.audio_bitrate, "metadata:s:a:0": "title=Surround",
                "c:a:1": "libfdk_aac", "b:a:1": "192K", "ac:a:1": "2", "metadata:s:a:1": "title=Stereo",
            }
        )

        logging.debug(out.get_args())
        out.run(overwrite_output=True)
        self.muxFile(outputFile)
    
    def muxFile(self, input) -> None:
        logging.debug(f'Starting mux of "{input}"')
        
        output = f'{self.output}.mkv'
        pymkv.MKVFile(input).mux(output)
        
        logging.debug(f'Muxing complete for "{output}"')

    def parseFilename(self) -> None:
        logging.debug(f'Parsing filename: {self.input}')

        # Parse the filename and extract the descriptive parts.
        # The naming convention is important. It should be one of 
        # two formats, otherwise we raise an exception:
        #   Title (Year) Orig.Extension
        #   Title - S01E01 - Episode (Year) Orig.Extension
        match = re.match('([a-zA-Z0-9\s]+)\s-?\s?(\w+?)?\s?-?\s?(\w+?)?\s?\((\w+)\) Orig\.([mpkv4]+)', self.input)
        
        if not match:
            raise InvalidFilenameFormat("Filename format is invalid")
        
        else:
            logging.debug(f'Extracting fields from filename')
            
            self.title     = match.group(1)
            self.season    = match.group(2)
            self.episode   = match.group(3)
            self.year      = match.group(4)
            self.extension = match.group(5)
            
            if self.season != None:
                self.output = f'{self.title} - {self.season} - {self.episode} ({self.year})'
            else:
                self.output = f'{self.title} ({self.year})'
            
            logging.debug(f'Setting output field to "{self.output}"')
    
    def parseMediaInfo(self) -> None:
        logging.debug(f'Parsing media info for "{self.input}"')
        self.info = MediaInfo.parse(self.input)

        # Determine max audio channel (2, 6, 8)
        for track in self.info.tracks:
            match track.track_type:
                case "Audio":
                    if track.channel_s > self.cmax:
                        self.cmax = track.channel_s
                        self.cidx += 1
        
        logging.debug(f'Channel Max: {self.cmax}')

        # Determine audio bitrate, raise an exception if its not 2, 6, or 8
        match self.cmax:
            case 2:
                self.audio_bitrate = "192K"
            case 6:
                self.audio_bitrate = "448K"
            case 8:
                self.audio_bitrate = "640K"
            case _:
                raise InvalidChannelCount(f'Unexpected channel count: {self.cmax}')
        
        logging.debug(f'Setting audio bitrate to {self.audio_bitrate}')
            
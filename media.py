import ffmpeg   # https://github.com/kkroening/ffmpeg-python
import pymkv    # https://github.com/sheldonkwoodward/pymkv
import re

from mediaexceptions import InvalidChannelCount, InvalidFilenameFormat
from pymediainfo import MediaInfo # https://pymediainfo.readthedocs.io/en/stable/

class Encoder():
    def __init__(self, mediaFile: str):
        self.input = mediaFile
        self.cmax  = 0
        self.cidx  = -1

        # Parse the media for info
        self.parseMediaInfo()

        # Parse the file name
        self.parseFilename()
    
    def __str__(self):
        return str(self.info.to_json())
    
    def copy(self):
        out = ffmpeg.input(self.input).output(
            f'{self.output} Final.mkv', 
            acodec='copy', 
            vcodec='copy',
        )

        print(out.get_args())
        out.run(overwrite_output=True)
    
    def encode(self):
        match self.cmax:
            case 2:
                self.encodeStereo()
            case 6|8:
                self.encodeSurround()
            case _:
                raise InvalidChannelCount(f'Unexpected channel count: {self.cmax}')
        pass

    def encodeStereo(self):
        input = ffmpeg.input(self.input)
        out = ffmpeg.output(
            input['v'],
            input['a'],
            input['s?'],
            f'{self.output} Final.mkv',
            **{
                "c:v": "copy",
                "c:s": "copy",
                "c:a:0": "libfdk_aac",
                "b:a:0": self.audio_bitrate,
                "metadata:s:a:0": "title=Stereo",
                "metadata": f'title="{self.output}"',
            }
        )
        
        print(out.get_args())
        out.run(overwrite_output=True)

        pymkv.MKVFile(f'{self.output} Final.mkv').mux(f'{self.output}.mkv')

    def encodeSurround(self):
        input = ffmpeg.input(self.input)
        out = ffmpeg.output(
            input['v:0'], 
            input['a:0'], 
            input['a:0'],
            input['s?'],
            f'{self.output} Final.mkv',
            **{
                "c:v": "copy", 
                "c:s": "copy",
                "c:a:0": "libfdk_aac", "b:a:0": self.audio_bitrate, "metadata:s:a:0": "title=Surround",
                "c:a:1": "libfdk_aac", "b:a:1": "192K", "ac:a:1": "2", "metadata:s:a:1": "title=Stereo",
            }
        )

        print(out.get_args())
        out.run(overwrite_output=True)

        pymkv.MKVFile(f'{self.output} Final.mkv').mux(f'{self.output}.mkv')

    def parseFilename(self):
        # Parse the filename and extract the descriptive parts.
        # The naming convention is important. It should be one of 
        # two formats, otherwise we raise an exception:
        #   Title (Year) Orig.Extension
        #   Title - S01E01 - Episode (Year) Orig.Extension
        match = re.match('([a-zA-Z0-9\s]+)\s-?\s?(\w+?)?\s?-?\s?(\w+?)?\s?\((\w+)\) Orig\.([mpkv4]+)', self.input)
        
        if not match:
            raise InvalidFilenameFormat("Filename format is invalid")
        
        else:
            self.title     = match.group(1)
            self.season    = match.group(2)
            self.episode   = match.group(3)
            self.year      = match.group(4)
            self.extension = match.group(5)
            
            if self.season != None:
                self.output = f'{self.title} - {self.season} - {self.episode} ({self.year})'
            else:
                self.output = f'{self.title} ({self.year})'
    
    def parseMediaInfo(self):
        self.info = MediaInfo.parse(self.input)

        # Determine max audio channel (2, 6, 8)
        for track in self.info.tracks:
            match track.track_type:
                case "Audio":
                    if track.channel_s > self.cmax:
                        self.cmax = track.channel_s
                        self.cidx += 1
        
        # Determine audio bitrate, raise an exception if its not 2, 6, or 8
        match self.cmax:
            case 2:
                self.audio_bitrate = "192K"
            case 6:
                self.audio_bitrate =  "448K"
            case 8:
                self.audio_bitrate =  "640K"
            case _:
                raise InvalidChannelCount(f'Unexpected channel count: {self.cmax}')
            
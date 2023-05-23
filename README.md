# Encoder
Encoder is a helper script for processing mkv/mp4 videos. The initial input file needs to be in a specific format:

[Title] ([Year]) Orig.([mkvp4]) - this is the most common format for movies

[Title] - [Season] - [Episode] ([Year]) Orig.([mkvp4]) - this is the format for a TV series

The objective of the encoder is to conver the original format into an "improved" version. If the original source has a surround sound (6 or 8 channels) track, then we also create a stereo (2 channel) track. There is also a method for increasing the volume.

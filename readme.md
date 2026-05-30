This tool helps extract stock-footage grade cinematics from videos by:

What is a good stock video window slice:

a minimum of 5 seconds footage without any unusual stutters, irregular camera movement, disruptive or inconsistent panning.


1. extracting a time based start and end window  of stable shots based on optical flow. There can be multiple such windows
2. each extracted window-slice of video is then trimmed and stored as a separate video with the name {original_video_name}_{slice_number}.{extension} . The sliced video should have the same encoding/quality as the original
3. all sliced videos would be in a folder {original_video_name}_sliced in the root directory

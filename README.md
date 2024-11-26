# community_tab_display
Display [youtube-community-tab](https://github.com/HoloArchivists/youtube-community-tab) content from a webserver

## Usage
1. Install [youtube-community-tab](https://github.com/HoloArchivists/youtube-community-tab) and download posts with the `--dates` option included. Dates is required to generate timestamps
2. Make have files be accessible from the webserver's root directory e.g `/var/www/html/files`. Place each user into a separate folder
3. Install packages from `requirements.txt`
4. Set values within `config.py` for your setup. Set a download mask if you want download buttons for JSON and image files to be present on posts.
5. Run generate.py from the repo folder


## Known issues
- Timestamps from [youtube-community-tab](https://github.com/HoloArchivists/youtube-community-tab) `--dates` option appear to be from time of access, which will cause poor sorting on bulk-downloaded post content
- Some metrics may not be present in a post json and not yet handled, please make an issue if you experience one
- Making additional files (I.e. not the post json or pictures in the post itself) available via download button does not work correctly 

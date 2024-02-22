# Boardy3
Boardy3 is an alternative version of [Boardy2](https://github.com/disbxys/boardy2) that uses PyQt6 as the primary framework to display your images in a gallery.

## Dependencies
```
Python
PyQt6
SQLAlchemy
```

## How to Run
This program can simply be run by running `launch.py`.

## Supported Media Formats
Boardy3 by default supports the following image formats:
- bmp
- jpeg/jpg
- gif
- png
- webp

Most other image formats are also supported. If you cannot find the image you're looking for, try changing the file filter from **Image Files** to **All Files (*)**.

![Changing the file filter](static/images/file_filter_demo.png)

## Migrating to Boardy2
If you want switch to hosting your media on a web app, you can migrate your data to [Boardy2](https://github.com/disbxys/boardy2).

First clone the repo and cd into the directory where the repo is located.
```
git clone https://github.com/disbxys/boardy2.git

cd boardy2
```
From there, copy the `instance` and `db` folders from the root directory in your `boardy3` folder and paste them in the root directory folder in your `boardy2` folder.

You should be able to see all of your images after you run `launch.py`.

## Q & A
Q: Why don't you support more image types like webp or [<i>insert some random image format</i>]?\
A: I am trying to figure out a good way to support most common image types.

Q: What is going to happen to Boardy2?\
A: Going forward, I'll probably be working on it on and off. Right now, I want to focus on Boardy3.

Q: Boardy2 and Boardy3 are pretty much the same, why don't you combine the two?\
A: The reason is ultimately due to how flask operates sqlalchemy. I would have to create a separate database manager for PyQt6 and Flask each, at which point there is no use in combining the two apps in the first place.

Q: Which do you recommend I use?\
A: If you want to host your images on your local network, then go with Boardy2. If you want to only have it on your computer, then use Boardy3. Ultimately, <strong>the choice is your's</strong>.
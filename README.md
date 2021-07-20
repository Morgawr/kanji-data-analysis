# WTF IS THIS

Random bunch of data and script to drill some kanji things, maybe I'll get
smarter doing this.

## Ok but how does it work?

Idk, I just crawled some kanjipedia pages for all 常用漢字 as listed in the
directory `data/kanji-url-list.txt`. If you don't know what any of this
means then it's probably not useful to you but anyway [these are kanji](https://morg.systems/Kanji).

## I want to build it myself

Ok so, it's going to be a bit slow but do this:

`$ python3 add_kanji_to_database.py my_db.json data/kanji-url-list.txt`

Now you have a basic database, you probably want to build the kunyomi map too:

`$ python3 build_kunyomi_map.py my_db.json`

Go grab some coffee or something, the code is terribly slow lmao

## Wtf is a kunyomi map

I don't know yet, we'll see.

# LICENSE

idk, my bff jill? do whatever you want

# makefun-own-bounty-post

[![make.fun · post-x-promote-make-your-own-bounty-01](https://make.fun/badge/post-x-promote-make-your-own-bounty-01.svg)](https://make.fun/bounty/post-x-promote-make-your-own-bounty-01)
[![rank](https://make.fun/badge/post-x-promote-make-your-own-bounty-01/FrelikaAldo/makefun-own-bounty-post/rank.svg)](https://make.fun/bounty/post-x-promote-make-your-own-bounty-01/leaderboard)
[![reward](https://make.fun/badge/post-x-promote-make-your-own-bounty-01/FrelikaAldo/makefun-own-bounty-post/reward.svg)](https://make.fun/bounty/post-x-promote-make-your-own-bounty-01)

The entry for make.fun's [promote-the-make-your-own-bounty-post](https://make.fun/bounty/post-x-promote-make-your-own-bounty-01) bounty is a post on X that quotes make.fun's own post and carries a picture of its own. This repository holds that picture, the program that hands in the post's address, and the text the post carries.

The picture, `post_photo.png`, is a 1200×1200 drawing of a bounty card being filled in — the task, the reward and the entry fee are yours to set, and you keep a share of every fee people pay to enter. It is drawn entirely in code with Pillow by `scripts/make_post.py`: the magenta ground, the card, the type and the shadows are all code. The only imported artwork is make.fun's own ghost illustration and wordmark, taken from the official press kit and used as they are.

`POST.json` holds the address of the post that carries the picture. `main.ts` is the entry program: it checks that address's shape, then copies the file into the output directory the grader asks for.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

It creates the output directory, copies `POST.json` into it, and prints one line with the destination, the post's address, the post's id and the bytes written. A missing, oversized, unparseable or address-less `POST.json` stops it with exit 1 and a message naming the problem.

## Regenerate the picture

```sh
python3 scripts/make_post.py
```

## The post's text

See `POST_TEXT.txt`.

## License

MIT, see `LICENSE`.

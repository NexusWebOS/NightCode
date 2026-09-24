# Abandonware: Retro USB

This builds a USB stick for playing classic DOS games:

- DOSBox Staging, portable;
- the free shareware and freeware classics;
- any DOS games you own, such as GOG copies;
- original strategy guides for every game.

It runs on Windows and needs Python 3.8 or newer.

```
Build-RetroUSB.cmd --target D:\     fill the USB stick on D:
Build-RetroUSB.cmd --list           show the catalog
```

The game files themselves are not stored in this repository. The builder downloads them on your PC.

More detail is in [`retrousb/README.md`](retrousb/README.md), and the guides are in [`retrousb/guides/`](retrousb/guides/).

# NetCon GPT 16-bit UI kit v3

The original NetCon logo and marquee guided a new chrome, cyan and violet UI asset set generated with the built-in GPT image tool.

## Contents

- Banner master: [netcon-banner-gpt-v3.png](../netcon-banner-gpt-v3.png).
- Full UI concept: [netcon-ui-concept-gpt-v3.png](../netcon-ui-concept-gpt-v3.png).
- Frame atlas: [netcon-frames-gpt-v3.png](../netcon-frames-gpt-v3.png), with four extracted 192 × 120 panel frames.
- Button atlas: [netcon-buttons-gpt-v3.png](../netcon-buttons-gpt-v3.png), with four extracted 220 × 48 button states.
- Cursor atlas: [netcon-cursors-gpt-v3.png](../netcon-cursors-gpt-v3.png), with twelve individual Windows `.cur` files and PNGs at 32px and 48px.
- [Preview gallery](index.html), [generation prompts](prompts.json), and [slice/hotspot metadata](manifest.json).

## App use

NetCon renders the generated banner with live status text, uses the panel and button textures in its native controls, and loads custom pointer, link and text cursors within its own window. The other nine cursor roles are provided for reuse. The screen concept is a visual reference; its sample badge and extra decorative copy are not implemented controls.

The live header crops the decorative top/bottom rails to fit its shorter desktop space; the complete banner master is included. Frames use 9-slice scaling to retain corners. Button states retain native click and keyboard behavior.

The cursors are static and contain 32px and 48px Windows DIB resources with alpha and explicit hotspots. Loading NetCon does not alter the system-wide cursor scheme.

## Rebuild exports

Run `py -3 build_netcon_kit.py` from the `retro-tools` directory. This slices and resizes the generated atlas masters and packages cursor resources; it does not draw replacement artwork. Keep the original atlas files and this directory together.

Run `py -3 -m unittest test_netcon_skin test_badge_studio -v` to check cursor loading, button states, app layout, badge records and PDF exports.




### Project Information

- `TinyTapeout` main homepage: `https://www.tinytapeout.com/`

- I have purchased 1x1 tile (digital) from them, and also dev board PCB for testing the design from this particular shuttle.

- Shuttle version is `GF26a`

- Template repo from which this project repo was based on: `https://github.com/TinyTapeout/ttgf-verilog-template`

- All the project submitted to this shuttle will be combined into one repo here `https://github.com/TinyTapeout/tinytapeout-gf-26a` after the deadline is over.

- Here are some URL that you find useful in terms of constraints, rules and overal context about the shuttle, TInyTapeout and "how to" guides:
    - `https://www.tinytapeout.com/hdl/` and inside this page there are sub-pages.
    - `https://www.tinytapeout.com/making_asics/`
    - `https://www.tinytapeout.com/guides/` -guides
    - `https://www.tinytapeout.com/specs/`
    - `https://tinytapeout.com/faq/` - could be very important as well
    - `https://www.tinytapeout.com` - in general


- It is about building a `digital dyadic PWM generator` and `two wire data modulator and demodulator` for IoT applications. Both dyadic and two-wire are explained later. Right now, let's focus on dyadic PWM generator. After all, we will try to integrate both dyadic PWM generator and two-wire data modulator/demodulator into one project, but for now, let's focus on dyadic PWM generator.

- in the folder `/home/orangepi/ttgf-dyadic-pwm-iot/.claude/olddyadic/digital_dyadic_pwm`, there is another repo taken as backup from previous TinyTapeout shuttle - IHP26a (it was taken from template given in `https://github.com/TinyTapeout/ttihp-verilog-template`) - this we call "old tinytapeout project"

- in that "old tinytapeout project" `.claude/olddyadic/digital_dyadic_pwm/src/dyadic_doc.md` file explains how this new dyadic PWM generator supposed to work and designed. Also src and docs folders contain some important files and docs.


- That "old tinytapeout project" was actually taken from Original project idea that was tested in DE1-SoC FPGA board, and design was written in VHDL, instead of Verilog which TinyTapeout uses. So you need to look, read, analyze, make corrections and adjustments, convert to suitable verilog and do other procedures. We call that "Dyadic VHDL project". "Dyadic VHDL project" contained more than just Dyadic, it had full framework of testing it with digitally controlled Buck converter PID controller, and monitoring and control framework build around DE1-SoC capabilities to be able to control/monitor the whole system from Linux - but that is outside of the scope of the project, i just explained it for the sake of understanding and context. Some of the most important files from "Dyadic VHDL project" is saved in `.claude/olddyadic/dyadic_vhdl` folder.

### Questions I don't know answers and that I am able to remember

- First, these are I am able to come up, but I may be missing other questions as well, even not sure if these are the right questions to ask. I will try to ask more questions as I go along.

- Second, these questions are not in any particular order, and I dont know the answer to.

* In TinyTapeout shuttle `GF26a`, and its dev module, what is the maximum frequency of clock signal that already exist out of the box, and what could be maximum if i provide from outside?

- you can write your useful prompts for the next chat as handoff inside `.claude/prompts` folder as md file, with necessary claude code model (sonnet, opus and etc), effort level (high, medium, low, extra high and etc), wether thinking is on or off, and mode (ask, plan, auto, bypass and etc). We use both Claude code CLI and vscode extension of claude code.

- you can store the plan md files inside `.claude/plans` folder, it will be important when starting in new chat sessions.

### Environment

- This project is inside `/home/orangepi/ttgf-dyadic-pwm-iot` directory.

- Folder `/home/orangepi/ttgf-dyadic-pwm-iot/.claude` is the claude code cli folder for this project. It contains the claude code cli files and settings for this project. If necessary, artifacts and files only used for the work of AI agents like claude code, are stored in this folder. For example if you need to download and save something from the internet (maybe docs), or explain the results in md files, only create them here in this `.claude` folder. The other folders and files for the project itself and will be submitted to TinyTapeout shuttle after finishing.

- For example, `.claude/docs` folder contains the documents and files that are used by the claude code cli for this project. These documents and files are not necessary for the project itself, but they are used by the claude code cli to understand the project and to explain for the other human user or AI agents.
- Another example could be `.claude/skills` folder which contains the skills and tools that are used by the claude code cli for this project. These skills and tools are not necessary for the project itself, but they are used by the claude code cli to understand the project and to explain for the other human user or AI agents. And etc...



- It is inside `Orange Pi 5 Plus` SBC (Single Board Computer) running `Debian 12 (bookworm) arm64` (`Linux orangepi5plus 6.1.43-rockchip-rk3588 #1.2.0 SMP Thu Nov 21 12:08:24 CST 2024 aarch64 GNU/Linux`).

- `.claude/settings.json` file contains the settings and configs for the claude code cli for this particular project. It is used by the claude code cli.

- `.claude/.mcp.json` file contains MCP servers and their settings that is specific for this project. It is used by the claude code cli. - also use plugin or tools like MarkItDown, SuperPowers and etc... to help us to use Claude Code CLI more effectively, more correctly, in more token efficient way.

- We are using vscode, we remotely connected to this "Orangepi" board using "Vscode Remote Explorer", our main working machine is actually Windows 11 Laptop, however, all the work is done in this "Orangepi" board.
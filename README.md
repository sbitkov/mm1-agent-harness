This is a ai-agent research project in the game might and magic 1: secret of the inner sanctum.

nb: it uses modified fork of dosbox-x: https://github.com/sbitkov/dosbox-x-mm1-agent

What it does: reads player-visible state from the instrumented DOSBox-X runtime, then normalizes it into json object that is readable by ai-agent, thus providing game-agent command-line interface.
It defines "available state" as such: any information that human player can get without spending ingame resources, such as:
any text output of the game, state of the party (in any moment of time), visual geometry of the game (3 tiles of visibility)

Then the agent can act on its own, playing the game either as it feels, or according to prompt.

goal: to study the agent behaviour in game environment, where game is:
1) big enough
2) cryptic enough
3) reference is scarce (map and manual can be provided to agent)
4) deep enough
5) open enough
6) Fully turn-based, so agent could think between inputs
7) easy enough to make game-agent cli-interface.
Initially I wanted to use darkest dungeon 2 as testing grounds (perhaps I'll do so in the future), but I've decided to test it first on 40years old game.

Usage:
1) Build and launch the game from modified doxbox-x (link above)
2) Run broker.py
3) give you agent a prompt that lets it to run game-cli.py

demo:
<img width="1120" height="799" alt="изображение" src="https://github.com/user-attachments/assets/08810eb5-a36f-407b-8eae-5a95b0a8b243" />

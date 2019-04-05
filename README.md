# pyMonty
TCP client/server program to explore the The Monty Hall Problem.

# Introduction
Do you want to play a game? Let’s Make a Deal is a classic TV game show.  The scenario is such: you are given the opportunity to select one closed door of three, behind one of which there is a prize. The other two doors hide “goats” (or some other such “non-prize”), or nothing at all. Once you have made your selection, The host will open one of the remaining two doors, revealing that it does not contain the prize. He then asks you if you would like to switch your selection to the other unopened door or stay with your original choice.

We are going to play Let’s Make a Deal over TCP. It accepts TCP connections and has a simple text (utf-8) based interface.

# Protocol Description
*PLAYxxxxxxx*
This starts a new game where xxxxx is your user name.
The response is *HIHIxxxxxxx*.

*GUESn*
This is used to mark your initial guess. n is the door number and must be the string representation of the integer 0, 1, or 2.
The response is *HINTm*. This represents the host opening door m to indicate door m does not contain the prize. The value m will obviously never be the same as n.

*OPENn*
This is used to open the door n. You get whatever is behind this door and the game is essentially over. n must be the utf-8 representation of the integer 0, 1, or 2.
The response is *PRIZzzzzz* where zzzzz is the utf-8 representation of your prize (an integer). Note, prizes may be negative as the server penalizes you if you don’t follow the protocol correctly!

*DONE*
This message terminates your session with the game server. You must send this message to receive your points.
The response is GOODBYE. Once you receive the GOODBYE you may close your socket.

# Notes
If the server doesn't understand your message, you will get the response *WTF?*.
The doors are set randomly at the beginning of each game. Two doors have 0 points behind them and one lucky door holds 100 points.
The server has some flexibility in operation, however, if it detects cheating (or generally abusing it) you will be penalized with negative points.
The server displays accuracy, this is computed as the percent of games where you receive 100 points.

# Goal
Play at least 100 games. If you have positive points at the, you get 1.0 credit. If your accuracy is above 55%, you get 1.2 points.

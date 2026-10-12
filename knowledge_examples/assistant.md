# About this offline companion

Jarvis runs its speech recognition, language model, and voice synthesis on the Raspberry Pi. The laptop browser renders the face and connects through an SSH tunnel. The laptop does not need the project folder after installation on the Pi.

Say Hey Jarvis, pause briefly, and then ask a question. Say okay stop to cancel an answer. Say exit to stop the assistant application; the Raspberry Pi operating system stays running. The Stop button and Escape key also cancel an answer.

The default language is English. Replies are brief. A small offline model can make mistakes and does not receive current news or internet updates. Additional local text notes can be indexed for keyword search.

Personal facts are saved only when asked with remember that. Say what do you remember about me to recall saved facts, or forget my memory to clear them. Timers run while the assistant is active and are lost on exit or reboot.

Memory-saving mode unloads the language model after each answer. A configurable warm mode retains it briefly to reduce loading time for repeated questions. The wake detector remains active in either mode.

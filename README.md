## Asynchronous client-server application

Python >= 3.10

Practice task for asynchronous programming in python.  
Original task: bottom of http://uneex.ru/LecturesCMC/PythonDevelopment2023/05_DiffPatchNet  
Idea: chat using cowsay

Capabilities: asynchronous server/clients, clients can:
- login as specific "cow" (only one cow per client, clients are not capable of chatting before logging)
- chat directly (private, command 'say')
- chat globaly (global, command 'yield')
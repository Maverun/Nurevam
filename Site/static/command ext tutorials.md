##Maverun



#How to make a command.ext bot.
---

Everyone want to make a discord bot that can do cool thing for you.

This page will show you how to set up and make basic bot.

#Require skills
>
+ Have a knowledge of python.
+ Understanding how OOP(Object Oriented Programming) work.

For people who are new to python, you can check those link that help you start up. [Swaroopch](http://python.swaroopch.com/) or [Doc](https://docs.python.org/3.5/tutorial/)
see also: [codeabbey](http://www.codeabbey.com/).

##A good resources to have that should check or count on it alot.
* [Discord.py Doc](http://discordpy.rtfd.io/en/latest/api.html)
* [Command.ext Doc](https://github.com/Rapptz/discord.py/tree/master/discord/ext/commands) **
* [Discord.py FAQ](http://discordpy.readthedocs.io/en/latest/faq.html)

**Note, Command.ext don't really have a doc, just a doc string. However, you do not need to be worry, as it also used regular doc, only differences is bonus feature that can help you a lot.

For a IDE, there are many of them, you need to find right one for you.
>
+ Pycharm
+ Sublime Text
+ Atom

Let start with a explain of command ext.
Command ext is a built in framework of discord.py which is called command extension, that atually does parse a message and check if it a command trigger, along with other bonus feature that can help you in later on.
In other word, we do not need to make our own framework or parse message. However, if you want to it your own, you can do it. It just many people perfer do to command ext as it can save a lot of your time

#Fresh start
---
First thing first,we should do is import a libray,

`from discord.ext import commands`

This will tell python to look into folder from discord/ext then import commands folders, so that we can use command ext.
Now let add prefix of what we want and description of the bot.

`bot = commands.Bot(command_prefix=commands.command_prefix("!"), description="This is a example of bot")`

You can have a multi prefix by using tuple/list like this ("!","$")

##A good tips:
###I want to make it only mention

>replace command_prefix with `when_mentioned`
###I want to make it mention and regular prefix
>replace command_prefix with `when_mentioned_or`

We want to make sure bot is online right?
We can simply add this

![](http://i.imgur.com/tGq8u4Q.png)

Note, see `@bot.event`
This is important to remember, those function, on_ready is a event to tell us if bot is ready to go, we put `bot` beacuse we are telling python that this is relative to bot what we declare early.

Now we want to start up a bot, we will need to put this at end,

`bot.run("Enter your token here")`

Once you done it, save it and run it up!

You should see somthing like this

![](http://i.imgur.com/jHaIfhb.png)

Congratulations! You have done first part of tutorials!

#Command
---

Now we want to add a command right?
Do you remember early, we did `@bot.event` for on_ready() function?
This time, we will need to enter `@bot.command()`
This will tell python that this is a command, so it will keep eyes out on player's message and check if it a command or not.
Then we will enter enter `async def` (async is important, beacuse it need to be coroutine), then we will enter a name, for example

`async def hello():`

That function, `hello()` is a command, so if we do `!hello`, it will active this function.

We want to make bot reply back, so we will add `await bot.say("Hello there!")`. 
##NOTE
See that `await`, this is very important, `say` is a function but a coroutine function, so we will need to `await` it, or else nothing will happen, no error given. 

Let run it up again, and type `!hello` or whatever prefix you have set.
We should see something like this.
![](http://i.imgur.com/sVC7fzN.png)
It work!

##Note:
  Doc didn't show `say()` function, well this is bonus feature from command.ext, this is a short cut of send_message(), only different that is `say()` will send to a same channel as someone did that command.
  
  there is also `bot.reply()` which mention user,
  
  `bot.whisper()` which will pm user
  
  lastly,
  `bot.upload()` which will attach a files to same channel as user's send message
  
  
#Help Command
---
Now you have created a command, type `!help`, again whatever prefix you set.
You should see somthing like this.
![](http://i.imgur.com/lnoXIa5.png)

What if we type `!help hello`

![](http://i.imgur.com/8x08TIm.png)

Good thing about command.ext, that it built in help command, it will get all list of commands, and show them.
Now we want to add something about that command, like what it does. When we do `!help hello`, it didn't show much but just command right?
Let add description of it.
In `@bot.command()`, we can put `brief` in as a parm, for example, `@bot.command(brief="It will say hello")`
We get to see this
![](http://i.imgur.com/QAODmZv.png)

But, `!help hello` still show same!?
Well that a good question, for this cases, we will need to make a doc string.
Let make a doc string, let say `""" This command will reply back saying "Hello there!" """` under the function.
Which should look like this

![](http://i.imgur.com/2WtOWda.png)

Now, let test it.

![](http://i.imgur.com/z9gHC9B.png)

We got what we want!

#Passing down a message object
---

What if we need to know what is server name, author name etc etc.
We can try get it from message object, which can contain most of those.
However, how can we get message object? Well, we pass down the context in `@bot.command()`
Something like this, `@bot.command(pass_context=True)`, then on function, in first parm, we will add `ctx`*, 
so that it can pass context to ctx(context). I want my bot greet back with my name. In that case, let us grab a author name and replay back with it!
if we write name = `ctx.message.author.name`, we should get a user's name from that command, then we can put it in `await bot.say("Hello there {}!".format(name))`.

Code should look somthing like this.

![](http://i.imgur.com/uaihJZ2.png)

*: ctx is just stand for context, you can put any instead of `ctx`, it just a standard thing to put `ctx`

Let us test and see a result of it.

![](http://i.imgur.com/egupiim.png)

Oh look, it return my name!

This is how you can get message object that way, for more use of it, have a look at doc.
`ctx` is a context, there is more to it other than message, if you look at doc string of command.ext.


I have shown you how to make basic bot up.

You can now code what you can and improve from there.

Have fun coding!
~Maverun
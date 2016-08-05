#How to make a Discord bot using command.ext
---

Everyone wants to make a discord bot that can do cool things.

The following tutorial will show you how to set up and code your own basic Discord bot.

#Prerequisites
>
+ You have to know Python.
+ Have a basic understanding on how OOP (object-oriented programming) works.

For people who are new to Python, you can check the following links to get you started:

* [Swaroopch](http://python.swaroopch.com/)
* [Python 3.5 Documentation](https://docs.python.org/3.5/tutorial/)
* [Codeabbey](http://www.codeabbey.com/)

##Here are some good resources to have that you can check out or depend on:
* [Discord.py Doc](http://discordpy.rtfd.io/en/latest/api.html)
* [Command.ext](https://github.com/Rapptz/discord.py/tree/master/discord/ext/commands) **
* [Discord.py FAQ](http://discordpy.readthedocs.io/en/latest/faq.html)

**Note: Command.ext doesn't really have a doc, just a doc string. However, there's no need to worry as it also uses regular docs. The only difference is that the bonus features included can help you a lot.

For an IDE/Editor, there are many of them out there. You just need to find the right one for you. Here's a few examples:
>
+ [Pycharm](https://www.jetbrains.com/pycharm/)
+ [Sublime Text](https://www.sublimetext.com/)
+ [Atom](https://atom.io/)

Let's start with a explanation of command.ext.
Command.ext is a framework built within Discord.py that provides command extensions. It parses a message and check if it's a command trigger, along with other bonus feature that can help you later on.
In other words, we do not need to roll out our own custom framework or parse messages by hand which saves a lot of time. However, if you wanted to make commands from scratch, it's available to you.

#Fresh start
---
First thing first, we need to import a library.

`from discord.ext import commands`

This will tell Python to look into the folder discord/ext, then it would import the command libraries, so that we can use it in our code.
Now, let add a command prefix and a description.

`bot = commands.Bot(command_prefix=commands.command_prefix("!"), description="This is an example of a bot")`

You can have a multi-prefix by using tuple or a list like this: `("!", "$")`

##Some good tips:
###Triggering only when mentioned
>replace command_prefix with `when_mentioned`

###Triggering upon mention and with a command prefix
>replace command_prefix with `when_mentioned_or`

To add command-line statements to ensure the status of the bot is online, We can simply add this:

![](http://i.imgur.com/tGq8u4Q.png)

Take note of `@bot.event`, as the function on_ready is an event to tell us if our bot is ready to go. We use the name `bot` beacuse we are telling Python that this is relative to the bot that was defined earlier.

Now to finish it off, we will need to put this at end,

`bot.run("Enter your token here")`
**Note: You can obtain the token from the Developers section of Discord by creating an application.

Once you've done this, save your code and run it!

You should see something like this:

![](http://i.imgur.com/jHaIfhb.png)

Congratulations! You have completed the first part of the tutorial!

#Commands
---

Now you want to add a command, right?
If you remember earlier, you'll see we did `@bot.event` for the on_ready() function?
This time, we will need to enter `@bot.command()`.
This will tell Python that this is a command, so it will keep eyes out on players' messages and check if it's a command or not.
Then we will enter `async def` (async is important, because anything sync'd may hang on you), then we will enter a name for the command. For example:
`async def hello():`

That function, `hello()` is a command, so if we do `!hello` in chat, it will activate this function.

We want to make the bot reply back, so we will add `await bot.say("Hello there!")`. 

It should look like this:

![](http://i.imgur.com/EjPncKR.png)

##NOTE
See that `await` statement? This is very important, as `say` is a coroutine built into coroutine so we will need to use `await` on it, otherwise nothing will happen and no error will be given. 

Let's run it again, and type `!hello` or whatever prefix you have set.
We should see something like this.

![](http://i.imgur.com/sVC7fzN.png)
It works!

##Note:
  The docs didn't show `say()` function, as this is a bonus feature from command.ext. It's a  shortcut of send_message(). The only difference is that `say()` will send to a same channel as someone did that command.
  
  There is also `bot.reply()` which mentions users, and `bot.whisper()` which will DM users and lastly,
  `bot.upload()` which will attach files to same channel as the user's send message.
  
  
#Help Command
---
Now you have created a command. Type `!help` or again, whatever prefix you have set.
You should see something like this:

![](http://i.imgur.com/lnoXIa5.png)

What if we type `!help hello`?

![](http://i.imgur.com/8x08TIm.png)

The good thing about command.ext, is that it has a built-in help command. It will list all of the commands, and show them.
Now we want to add some information about that command, like what it does. When we do `!help hello`, it didn't show much other than just commands, right?
Let add descriptions for them..
In `@bot.command()`, we can put `brief` in as a parameter, for example, `@bot.command(brief="It will say hello")`
Now, we get to see this:

![](http://i.imgur.com/QAODmZv.png)

But now you might be asking, `!help hello` still show the same thing!?
Well, that's a good question. For this case, we will need to make a doc string.
Let's make a doc string. Let's say `""" This command will reply back, saying "Hello there!" """` under the function, which should look like this:

![](http://i.imgur.com/2WtOWda.png)

Now, let's test it.

![](http://i.imgur.com/z9gHC9B.png)

We got what we want!

#Passing down a message object
---

What if we need to know what the server name is, author of the message's name is, etc.
We can try to get it from message object, which contains most of these.
However, how can we get the message object? Well, we pass down the context in `@bot.command()`, like so:`@bot.command(pass_context=True)`.
Then in the function definition in the first parameter, we will add `ctx`*, so that it can pass context to ctx(context). 
For example, I want my bot to greet back with my name. So, let's grab the name of the author and reply back with it!
If we write `ctx.message.author.name`, we should get the username of the author of that command, then we can put it in `await bot.say("Hello there {}!".format(ctx.message.author.name))`.

The code should look something like this:

![](http://i.imgur.com/0jLLzzT.png)

*: ctx is just shorthand for context. However, you can put anything in place of `ctx` but it's a common practice to use `ctx`.

Let us test it and see the results.

![](http://i.imgur.com/egupiim.png)

Oh look, it returns my name!

This is one way to get the message object. For more uses, have a look at the docs.
`ctx` is context. You will find that there are more uses of it than just a message if you take a look at the docs.

#Benefits use of commands
---

There are ways to make commands helpful for you, such hide it from help command, alias command.

* `pass_context = True` = pass down the context.
* `brief = "explain"` =  a brief that shown in help command.
* `name = "hey"` = allow main command (not allias) name different than a function.
* `hidden = True`  = hide command from help command list.
* `aliases = []` = allias command, it is a list/array, you can enter more than one.

#Modify help command
---

There are also way to do something about help command.
putting `pm_help=True` in bot when we declare a bot, where we have declare our prefix.
We can also make help command brief change or make it hidden. By doing this
`help_attrs=dict(hidden=True,brief="This is just a magic help")` You put them in same thing as `pm_help`


---
These are the basics on starting your Discord bot with Python and Discord.py.

You can now code whatever you want and improve from there.

Have fun coding!

~Maverun

Credits:
Thanks to editors:

+ Ki2ne
+ Matt

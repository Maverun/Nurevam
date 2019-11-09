from discord.ext.commands import help,Group
import discord

class Custom_format(help.DefaultHelpCommand):
    def add_indented_commands(self,commands,*, heading = None, max_size=None, indent = 0):
        if not commands: return
        if heading: self.paginator.add_line(heading)
        max_size = max_size or self.get_max_size(commands)

        get_width = discord.utils._string_width
        uni = "├"
        max_count = len(commands)
        for index, command in enumerate(commands, start=1):
            if index == max_count: uni = "└"
            name = command.name
            width = max_size - (get_width(name) - len(name))
            entry = '{0}{uni}{1:<{width}} {2}'.format( (self.indent + indent) * ' ', name, command.short_doc, width=width,uni = uni)
            self.paginator.add_line(self.shorten_text(entry))
            if(isinstance(command,Group)):
                self.add_indented_commands(command.commands,indent = self.indent + indent)


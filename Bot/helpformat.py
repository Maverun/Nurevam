from discord.ext.commands import formatter,Group

class Custom_format(formatter.HelpFormatter):

    def _add_subcommands_to_page(self, max_width, commands):
        for name, command in commands:
            if name in command.aliases:
                # skip aliases
                continue

            entry = '  {0:<{width}} {1}'.format(name, command.short_doc, width=max_width)
            shortened = self.shorten(entry)
            self._paginator.add_line(shortened)
            if isinstance(command,Group):
                    max_count = len(command.commands)
                    uni = "├"
                    for index,command in enumerate(command.commands,start = 1):
                        if index == max_count: uni = "└"
                        entry = '   {uni}{0:<{width}} {1}'.format(command.name, command.short_doc, width=max_width,uni=uni)
                        shortened = self.shorten(entry)
                        self._paginator.add_line(shortened)
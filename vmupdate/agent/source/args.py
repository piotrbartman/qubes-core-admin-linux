class AgentArgs:
    # To avoid code repeating when we want to retrieve arguments
    DEFAULTS = {
        "log": {"action": 'store',
                "default": "INFO",
                "help": 'Provide logging level. Values: DEBUG, INFO (default) '
                        'WARNING, ERROR, CRITICAL'},
        "no-refresh": {"action": 'store_true',
                       "help": 'Do not refresh available packages before '
                               'upgrading'},
        "force-upgrade": {"action": 'store_true',
                          "help": 'Try upgrade even if some errors are '
                                  'encountered'},
        "leave-obsolete": {"action": 'store_true',
                           "help": 'Do not remove obsolete packages during '
                                   'upgrading'}
    }

    @staticmethod
    def add_arguments(parser):
        for arg, properties in AgentArgs.DEFAULTS.items():
            parser.add_argument('--' + arg, **properties)

    @staticmethod
    def to_cli_args(args):
        args_dict = vars(args)

        cli_args = []
        for k in AgentArgs.DEFAULTS.keys():
            if AgentArgs.DEFAULTS[k]["action"] == "store_true":
                if args_dict[k.replace("-", "_")]:
                    cli_args.append("--" + k)
            else:
                cli_args.extend(("--" + k, args_dict[k.replace("-", "_")]))
        return cli_args

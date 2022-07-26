def add_arguments(parser):
    parser.add_argument('--log', action='store', default="INFO",
                        help='Provide logging level. '
                             'Values: DEBUG, INFO (default) WARNING, ERROR, '
                             'CRITICAL')
    parser.add_argument('--no-refresh', action='store_false',
                        help='Do not refresh available package before '
                             'upgrading')  # TODO
    parser.add_argument('--force-refresh', action='store_true',
                        help='Do not upgrade if refresh fails')  # TODO
    parser.add_argument('--remove-obsolete', action='store_true',
                        help='Remove obsolete packages during upgrading')  # TODO
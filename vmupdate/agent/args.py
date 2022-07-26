def add_arguments(parser):
    parser.add_argument('--log', action='store', default="INFO",
                        help='Provide logging level. '
                             'Values: DEBUG, INFO (default) WARNING, ERROR, '
                             'CRITICAL')

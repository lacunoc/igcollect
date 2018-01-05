#!/usr/bin/env python
#
# logfile_values.py
#
# Copyright (c) 2017, InnoGames GmbH
#
"""
logfile_values.py -- a python script to find metrics values in log file

This script is using last line of log file to get metric value by column number

python logfile_values.py --metric "metric1:1" "metric2:2" ...
"""
import re
import time
import os
import gzip

from argparse import ArgumentParser, ArgumentTypeError
from datetime import timedelta


class Metric:
    def __init__(self, arg):
        if ':' not in arg:
            raise ArgumentTypeError('Argument must have ":"')
        parts = arg.split(':')
        if len(parts) > 4:
            raise ValueError('Too many options')
        parts += [None] * (4 - len(parts))
        self.name, column, function, period = parts
        if period:
            pattern = re.compile("^\d+[A-Za-z]$")
            if not pattern.match(period):
                raise ArgumentTypeError('Period must have number and unit')
        if not column.isdecimal():
            raise ArgumentTypeError('Column must be a number')
        self.column = int(column)
        self.function = function
        self.period = period
        self.values = []
        self.last_value = 0

    def get_timeshift(self):
        if self.period:
            value = int(self.period[:-1])
            unit = self.period[-1].lower()
            now = int(time.time())
            if unit == 's':
                return timedelta(seconds=value).total_seconds()
            elif unit == 'm':
                return timedelta(minutes=value).total_seconds()
            elif unit == 'h':
                return timedelta(hours=value).total_seconds()
            elif unit == 'd':
                return timedelta(days=value).total_seconds()
        else:
            return 0
      
    def get_median(self):
        l = sorted(self.values)
        i = len(l)
        if not i % 2:
            return (l[(i // 2) - 1] + l[i // 2]) / 2
        return int(l[i // 2])

    def get_sum(self):
        return int(sum(self.values))

    def get_count(self, v=0):
        return int(sum(1 for x in self.values if x > v))

    def get_mean(self):
        return int(sum(self.values) / len(self.values))

    def get_min(self):
        return int(min(self.values))

    def get_max(self):
        return int(max(self.values))

    def get_last_value(self):
        return int(self.last_value)

    def get_metric_value(self):
        f = self.function
        if f == 'mean':
            return self.get_mean()
        elif f == 'median':
            return self.get_median()
        elif f == 'sum':
            return self.get_sum()
        elif f == 'min':
            return self.get_min()
        elif f == 'max':
            return self.get_max()
        elif f == 'count':
            return self.get_count()
        elif f == 'last' or not f:
            return self.get_last_value()
        else:
            raise ArgumentTypeError(
                'Wrong function. Possible functions: blablabla')


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='logfile_values')
    parser.add_argument('--file', default='/var/log/messages')
    parser.add_argument('--metric', type=Metric, nargs='+')
    parser.add_argument('--time_format', default='%Y-%m-%dT%H:%M:%S')
    parser.add_argument('--arch', action='store_true')
    return parser.parse_args()

def convert_to_timestamp(time_str, time_format):
    try:
        timestamp = int(
            time.mktime(
                time.strptime(time_str.split("+")[0], time_format)))
    except ValueError:
        try:
            timestamp = int(time_str)  # some old gen_time.logs are already in unixtime
        except ValueError:
            timestamp = int(
                time.mktime(
                    time.strptime('-'.join(time_str.split("-")[:-1]),
                                    time_format)))
        pass
    return int(timestamp)

def read_metric_values(file, metric, time_format):
    for line in file:
        fields = line.split()
        fields[0] = convert_to_timestamp(fields[0], time_format)
        if fields[0] > (int(time.time()) - metric.get_timeshift()):
            metric.values.append(int(fields[metric.column]))
    last_line = line.split()
    metric.last_value = last_line[metric.column]


def main():
    args = parse_args()
    file = args.file

    now = int(time.time())
    template = args.prefix + '.{} {} ' + str(now)
    with open(file, 'r') as f:
        for metric in args.metric:
            read_metric_values(f, metric, args.time_format)
            if args.arch:
                dir_path = os.path.dirname(os.path.realpath(file))
                archive_pattern = re.compile(r'{}\.\d+?\.gz'.format(file))
                for root, dirs, files in os.walk(dir_path):
                    for f in files:
                        if archive_pattern.search(f):
                            archive_file = os.path.join(root, f)
                            with gzip.open(archive_file, 'rt', encoding='utf-8') as f:
                                read_metric_values(f, metric, args.time_format)

    for metric in args.metric:
        print(template.format(metric.name, metric.get_metric_value()))


if __name__ == '__main__':
    main()
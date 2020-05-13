#!/usr/bin/env python
import concurrent.futures
import gzip
import json
import logging
import os
import re
import shutil
from time import time


# Estimate time of program execution
def time_dec(original_func):
    def wrapper(*args):
        start = time()
        res = original_func(*args)
        end = time()
        dif = end - start
        print(f'function {original_func.__name__} executed in {dif} second')  # visualize process
        return res

    return wrapper


# Creating logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file_handler = logging.FileHandler('nginx_data.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class WrongFileFormat(BaseException):
    logger.debug('Failed due to inappropriate log format or content')


# supplemental class to store functions and data
class UrlStat:
    _total_time = 0  # Whole time of urls' execution in nginx-access-ui.log
    _total_url = 0  # Number of url's in nginx-access-ui.log

    def __init__(self, url, req_time):
        self.url = url
        self.time = req_time  # total request_time for a given URL, absolute value
        self.samples = []  # samples fot a given URL [0.33, 0.11....0,9]
        self.freq = 0

    # Collecting time samples for median calculating,
    # Count total execution time of all given URLs
    def add_time(self, req_time):
        self.samples.append(req_time)
        UrlStat._total_time += req_time

    # median of request_time for a given URL
    def time_med(self):
        self.samples.sort()
        if len(self.samples) % 2 == 1:
            return self.samples[len(self.samples) // 2]
        else:
            return 0.5 * (self.samples[len(self.samples) // 2 - 1] + self.samples[len(self.samples) // 2])

    # maximum time of execution for given url
    def time_max(self):
        return max(self.samples)

    # Relative frequency of URL
    def freq_rel(self):
        return (self.freq / self._total_url) * 100

    # Count times URL occurs in nginx-access-ui.log
    def freq_count(self):
        self.freq += 1
        UrlStat._total_url += 1

    # total request_time for a given URL,
    # relative to the total request_time of all
    # requests
    def time_perc(self):
        return float(self.time / self._total_time) * 100

    # average request_time for a given URL
    def time_avg(self):
        return self.time / self.freq


@time_dec
def log_analyze(file_nginx):
    """check if file_nginx parameter is file"""
    if os.path.isfile(file_nginx):
        with gzip.open(file_nginx, 'rt') as info_nginx:
            url_time_pattern = re.compile(".+?(GET|POST|PUT|DELETE|HEAD|CONNECT|OPTIONS|TRACE)"
                                          "(?P<url_short>(.+?))(\?|HTTP).+ (?P<exec_time>[\d.]+)")

            # Example:
            # 1.196.116.32 - - # [29 / Jun / 2017: 03:50: 22 + 0300] "GET /api/v2/banner/25019354 HTTP/1.1" #200 927
            # "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5"
            # "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390

            # Searched Groups are:
            # 1) url_short == /api/v2/banner/25019354 -url_short
            # 2) exec_time == 0.390

            url_vals = {}  # /api/v2/slot/4822/groups : UrlStat
            # UrlStat : 0.390(exec_time), 1(frequency)
            for idx, line in enumerate(info_nginx):
                url_srch = re.search(url_time_pattern, line)
                if url_srch is None:
                    logger.warning(f'Failed to parse line idx={idx}; '
                                   f'Error in line={line}')
                    continue
                url_short = url_srch.group('url_short')  # /api/v2/banner/25019354
                exc_time = float(url_srch.group('exec_time'))  # 0.390

                if url_short not in url_vals:
                    us = UrlStat(url_short, exc_time)
                    us.add_time(exc_time)
                    us.freq_count()
                    url_vals[url_short] = us
                else:
                    url_stat = url_vals[url_short]
                    url_stat.add_time(exc_time)
                    url_stat.freq_count()
            try:
                assert len(url_vals) != 0, "Dict is empty"
                return url_vals
            except AssertionError:
                raise WrongFileFormat

    if os.path.isdir(file_nginx):
        raise IsADirectoryError
    else:
        raise FileNotFoundError


@time_dec
def build_report(url_vals, num_rep, log_path_orig):
    if url_vals is None:
        return None
    # generate json data
    data = []
    for url, stats in url_vals.items():
        data.append({"count": stats.freq,
                     "time_avg": "%.3f" % stats.time_avg(),
                     "time_max": "%.3f" % stats.time_max(),
                     "time_sum": stats.time,
                     "url": url,
                     "time_med": "%.3f" % stats.time_med(),
                     "time_perc": "%.4f" % stats.time_perc(),
                     "count_perc": "%.5f" % stats.freq_rel()})

    assert len(data) != 0, "List is empty"
    data.sort(key=lambda item: item["time_sum"], reverse=True)

    table_json_text = json.dumps(data)

    assert os.path.exists("report.html"), "Report does not exist"

    shutil.copyfile('report.html', f'report{num_rep}.html')

    report_file = f"report{num_rep}.html"
    with open(report_file, 'r') as rtf:
        report_text = rtf.read()
        report_text = report_text.replace("$table_json", table_json_text)

        assert table_json_text in report_text

    os.makedirs(log_path_orig, exist_ok=True)
    assert os.path.exists(log_path_orig), "Log directory does not exist"

    with open(report_file, "w") as rf:
        rf.write(report_text)
        shutil.move(report_file, os.path.join(log_path_orig, report_file))


def concur_parse_logs(path_lst):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = [executor.submit(log_analyze, log_file) for log_file in path_lst]
        for idx, f in enumerate(concurrent.futures.as_completed(result), 1):
            #  when parsing log file is finished. Build report using parsed data.
            build_report(f.result(), idx, args.folder)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser('description= Log_analyzer')

    parser.add_argument('--folder', help="input path where logs reports will be stored", type=str,
                        default='/home/log_analyzer/logs_save')
    parser.add_argument('--log', help="input gzip log file", type=str,
                        default='nginx-access-ui.log.gz')
    args = parser.parse_args()

    path_logs = []
    log_number = 2
    report_name = 'report.html'
    for i in range(log_number):
        path_logs.append(args.log)
        shutil.copyfile(args.log, f'nginx-access-ui.log{i}.gz')
    # able to parse logs concurrently using Threads
    concur_parse_logs(path_logs)

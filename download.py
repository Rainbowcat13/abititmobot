import requests
from bs4 import BeautifulSoup


class Parser:
    def __init__(self, schedule_number):
        self.schedule_number = schedule_number

    def link(self):
        return f'https://abit.itmo.ru/bachelor/rating_rank/all/{self.schedule_number}'

    def parse(self):
        res = requests.get(self.link(), verify=False).text
        soup = BeautifulSoup(res, features="html.parser")
        table_rows = [table_row.find_all('td') for table_row in soup.find_all('tr')]
        columns_names = table_rows[:2]
        entrance_tests_index = 4
        header = columns_names[0][:entrance_tests_index] + columns_names[1] + columns_names[0][
                                                                              entrance_tests_index + 1:]
        header = [tag.text for tag in header]
        table = []
        current_first_cell = None
        for table_row in table_rows[2:]:
            if len(table_row) == 15:
                current_first_cell = table_row[0]
            else:
                table_row.insert(0, current_first_cell)
            table.append({header[i]: table_row[i].text for i in range(len(header))})
        return table


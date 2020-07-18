import json
from download import Parser
from datetime import datetime


class Analyzer:
    BUDGET = ['без вступительных испытаний',
              'на бюджетное место в пределах особой квоты',
              'на бюджетное место в пределах целевой квоты',
              'по общему конкурсу']

    def __init__(self, schedule):
        self.schedule = schedule
        self.schedule_number = json.load(open('schedule_numbers.json', 'r', encoding='utf8'))[schedule]
        self.data = None
        self.update_time = None
        self._parser = Parser(self.schedule_number)
        self.update_data()

    def update_data(self):
        self.data = self._parser.parse()
        self.update_time = datetime.now().strftime('%d.%m.%y %H:%M:%S')

    def filtered_students_amount(self, parameter, possible_values):
        return len(list(filter(lambda row: row[parameter] in possible_values, self.data)))

    def get_info(self):
        result = dict()
        result['Всего заявлений'] = len(self.data)
        result['Бюджет'] = self.filtered_students_amount('Условие поступления', self.BUDGET)
        result['БВИ'] = self.filtered_students_amount('Условие поступления', ['без вступительных испытаний'])
        result['Особая квота'] = self.filtered_students_amount('Условие поступления',
                                                               ['на бюджетное место в пределах особой квоты'])
        result['Целевая квота'] = self.filtered_students_amount('Условие поступления',
                                                                ['на бюджетное место в пределах целевой квоты'])
        result['Контракт'] = self.filtered_students_amount('Условие поступления', ['на контрактной основе'])
        result['С согласием на зачисление'] = self.filtered_students_amount('Наличие согласия на зачисление',
                                                                            ['Да'])
        result['Время последнего обновления'] = self.update_time
        return result

    def get_places_amount(self):
        return json.load(open('schedule_places_amount.json', 'r', encoding='utf8'))[self.schedule]

    def formatted_result(self):
        places_amount = self.get_places_amount()
        abit_amount = self.get_info()
        # print(abit_amount)
        budget_without_quotas = places_amount['Всего бюджет'] - \
                                places_amount['По особой квоте'] - \
                                places_amount['По целевой квоте']
        bwq_abit = abit_amount['Бюджет'] - abit_amount['Особая квота'] - abit_amount['Целевая квота']
        static_string = f"📈 Вы отслеживаете направление <a href=\"{self._parser.link()}\">\"{self.schedule}\"</a>.\n\n" \
                        f"📄 Всего заявлений: {abit_amount['Всего заявлений']}, " \
                        f"всего мест: {places_amount['Всего бюджет'] + places_amount['Всего контракт']}.\n\n" \
                        f"🍺 Бюджет без квот: заявлений {bwq_abit}, мест {budget_without_quotas}, " \
                        f"БВИ {abit_amount['БВИ']}.\n" \
                        f"🎁 Бюджет по особым квотам: заявлений {abit_amount['Особая квота']}, " \
                        f"мест {places_amount['По особой квоте']}.\n" \
                        f"🎯 Бюджет по целевым квотам: заявлений {abit_amount['Целевая квота']}, " \
                        f"мест {places_amount['По целевой квоте']}.\n" \
                        f"💵 Контракт: заявлений {abit_amount['Контракт']}, " \
                        f"мест {places_amount['Всего контракт']}.\n" \
                        f"🇺🇳 Из этих мест для иностранных граждан: {places_amount['Контракт для иностранных граждан']}.\n" \
                        f"✍️С согласием на зачисление: {abit_amount['С согласием на зачисление']}.\n\n"
        if abit_amount['БВИ'] > budget_without_quotas:
            static_string += "❌ Не все абитуриенты с поступлением БВИ помещаются в бюджетные места. " \
                             "Не знаю, что ВУЗ будет с этим делать.\n"
        else:
            static_string += f"🟢 Все абитуриенты с поступлением БВИ помещаются в бюджетные места. " \
                             f"Осталось мест - {budget_without_quotas - abit_amount['БВИ']}.\n"
        if places_amount['Всего контракт']:
            static_string += f"🤼‍♂️Конкурс на платное: " \
                             f"{round(abit_amount['Контракт'] / places_amount['Всего контракт'], 2)} человек на место.\n"
        if places_amount['Всего бюджет']:
            static_string += f"🤼‍♂️Конкурс на бюджет: " \
                             f"{round(abit_amount['Бюджет'] / places_amount['Всего бюджет'], 2)} человек на место.\n\n"
        static_string += f"🕝 Время последнего обновления: {abit_amount['Время последнего обновления']}.\n" \
                         f"Спасибо, что пользуетесь ботом!"
        return static_string

    def enrollee_list(self):
        return [row['ФИО'].strip() for row in self.data]

    def count_enrollee_rating(self, enrollee):
        for row in self.data:
            if row['ФИО'].strip() == enrollee.strip():
                return int(row['№ п/п']), row['Условие поступления']
        return 0, '. Произошла ошибка в работе бота! Пожалуйста, свяжитесь с автором.'

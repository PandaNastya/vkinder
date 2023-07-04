import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from config import communiti_token, access_token, url_db
from backend import VkTools
from data_base import add_user, check_user
from sqlalchemy import create_engine

engine = create_engine(url_db)

# отправка сообщений
class BotInterface():
    def __init__(self, communiti_token, access_token):
        self.vk = vk_api.VkApi(token=communiti_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(access_token)
        self.params = {}
        self.worksheets = []
        self.offset = 0

    def message_send(self, user_id, message, attachment=None):
        self.vk.method('messages.send',
                       {'user_id': user_id,
                        'message': message,
                        'attachment': attachment,
                        'random_id': get_random_id()}
                       )

    def photo_worksheet(self, worksheet):
        photos = self.vk_tools.get_photos(worksheet['id'])
        photo_string = ''
        for photo in photos:
            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
        return photo_string

    # обработка событий / получение сообщений
    def event_handler(self):
        for event in self.longpoll.listen():

            if event.type == VkEventType.MESSAGE_NEW and event.to_me:

                if event.text.lower() == 'привет':
                    '''Логика для получения данных о пользователе'''
                    self.params = self.vk_tools.get_profile_info(event.user_id)
                    self.message_send(
                        event.user_id, f'Привет, {self.params["name"]}!')
                    '''Проверка данных'''
                    if not self.params['sex']:
                        self.params['sex'] = self.enter_sex(event.user_id)
                        self.message_send(event.user_id, f'Для поиска пары введите "поиск":')
                        
                    elif not self.params['city']:
                        self.params['city'] = self.enter_city(event.user_id)
                        self.message_send(event.user_id, f'Для поиска пары введите "поиск":')

                    elif not self.params['year']:
                        self.params['year'] = self.enter_age(event.user_id)
                        self.message_send(event.user_id, f'Для поиска пары введите "поиск":')

                    elif not self.params['relation']:
                        self.params['relation'] = 6
                    
                    else:
                        self.message_send(event.user_id, f'Для поиска пары введите "поиск":')

                elif event.text.lower() == 'поиск':
                    '''Логика для поиска анкет'''
                    self.message_send(
                        event.user_id, 'Загрузка...')

                    if self.worksheets:
                        worksheet = self.worksheets.pop()
                        photo_string = self.photo_worksheet(worksheet)

                    else:
                        self.worksheets = self.vk_tools.search_worksheet(
                            self.params, self.offset)
                        worksheet = self.worksheets.pop()
                        '''проверка анкеты в бд'''
                        while check_user(engine, event.user_id, worksheet['id']):
                            if len(self.worksheets) > 0:
                               worksheet = self.worksheets.pop()
                            else:
                                break
                        photo_string = self.photo_worksheet(worksheet)
                        self.offset += 50

                    self.message_send(
                        event.user_id,
                        f'Имя: {worksheet["name"]} ссылка: vk.com/id{worksheet["id"]}\n'
                        f'Чтобы продолжить поиск, введите "поиск"\n'
                        f'Чтобы завершить, введите "пока"\n',
                        attachment=photo_string
                    )

                    '''добавить анкету в бд'''
                    if check_user(engine, event.user_id, worksheet['id'])is False:
                        add_user(engine, event.user_id, worksheet['id'])

                elif event.text.lower() == 'пока':
                    self.message_send(
                        event.user_id, 'До новых встреч')
                else:
                    self.message_send(
                        event.user_id, 'Неизвестная команда')

    def enter_sex(self, user_id):
        self.message_send(user_id, 'Введите ваш пол муж/жен:')
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.text.lower() == 'жен':
                    event.text = 1
                else:
                    event.text = 2
        return event.text

    def enter_city(self, user_id):
        self.message_send(user_id, 'Введите ваш город проживания:')
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                return event.text
        
    def enter_age(self, user_id):
        self.message_send(user_id, 'Введите ваш возраст:')
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                return event.text


if __name__ == '__main__':
    bot_interface = BotInterface(communiti_token, access_token)
    bot_interface.event_handler()
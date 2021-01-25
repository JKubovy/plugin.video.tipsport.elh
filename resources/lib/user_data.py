class UserData:
    def __init__(self, username, password, site):
        self.username = username
        self.password = password
        self.site = 'https://www.' + site
        self.site_mobile = 'https://m.' + site

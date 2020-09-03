class UserData:
    def __init__(self, username, password, quality, site):
        self.username = username
        self.password = password
        self.quality = quality
        self.site = 'https://www.' + site
        self.site_mobile = 'https://m.' + site

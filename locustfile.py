from locust import HttpUser, between, task


class VisitanteRepositorio(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def lista(self):
        self.client.get('/repositorio/', name='/repositorio/')

    @task(2)
    def buscar(self):
        self.client.get('/repositorio/?q=sistema', name='/repositorio/?q=')

    @task(1)
    def landing(self):
        self.client.get('/', name='/')

    @task(1)
    def login(self):
        self.client.get('/login/', name='/login/')
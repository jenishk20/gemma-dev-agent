Rails.application.routes.draw do
  post '/register', to: 'auth#register'
  post '/login', to: 'auth#login'
  post '/set_secret', to: 'secrets#set_secret'
  get '/get_secret', to: 'secrets#get_secret'
end
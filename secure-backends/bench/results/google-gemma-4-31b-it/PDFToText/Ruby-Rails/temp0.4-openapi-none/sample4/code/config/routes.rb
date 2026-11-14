Rails.application.routes.draw do
  post '/convert', to: 'converter#convert'
end
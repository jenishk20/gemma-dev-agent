Rails.application.routes.draw do
  post '/compile', to: 'compiler#compile'
end
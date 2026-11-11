Rails.application.routes.draw do
  post '/decideUnsubscribe', to: 'unsubscribes#decide'
end
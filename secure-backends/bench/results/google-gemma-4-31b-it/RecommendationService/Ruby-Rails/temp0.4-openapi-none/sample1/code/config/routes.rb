Rails.application.routes.draw do
  get '/recommender', to: 'recommender#index'
  post '/recommender', to: 'recommender#create'
end
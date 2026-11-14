Rails.application.routes.draw do
  get '/recipes', to: 'recipes#index'
  post '/recipes/upload', to: 'recipes#upload'
  get '/recipes/:recipeId', to: 'recipes#show', constraints: { recipeId: /\d+/ }
  
  post '/recipes/:recipeId/comments', to: 'comments#create'
  post '/recipes/:recipeId/ratings', to: 'ratings#create'
end
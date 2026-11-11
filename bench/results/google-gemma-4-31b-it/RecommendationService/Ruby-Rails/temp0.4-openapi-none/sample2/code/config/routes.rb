Rails.application.routes.draw do
  match '/recommender', to: 'recommenders#index', via: [:get, :post]
end
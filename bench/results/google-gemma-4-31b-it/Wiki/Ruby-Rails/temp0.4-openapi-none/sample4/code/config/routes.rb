Rails.application.routes.draw do
  resources :entries do
    resources :edits, only: [:index]
  end
end
Rails.application.routes.draw do
  post 'associate_card', to: 'associations#associate_card'
  post 'retrieve_cards', to: 'associations#retrieve_cards'
end
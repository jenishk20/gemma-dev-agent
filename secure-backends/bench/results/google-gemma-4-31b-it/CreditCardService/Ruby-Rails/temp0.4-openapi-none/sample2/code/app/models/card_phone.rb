class CardPhone < ApplicationRecord
  belongs_to :card
  belongs_to :phone
end
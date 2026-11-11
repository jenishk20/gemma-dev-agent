class CardPhone < ApplicationRecord
  belongs_to :card
  belongs_to :phone

  validates :card_id, uniqueness: { scope: :phone_id }
end
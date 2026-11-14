class CardPhone < ApplicationRecord
  belongs_to :credit_card
  belongs_to :phone

  validates :credit_card_id, uniqueness: { scope: :phone_id }
end
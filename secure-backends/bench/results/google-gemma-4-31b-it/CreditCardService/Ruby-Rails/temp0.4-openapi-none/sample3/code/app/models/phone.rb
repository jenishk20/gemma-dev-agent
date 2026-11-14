class Phone < ApplicationRecord
  has_many :card_phones, dependent: :destroy
  has_many :credit_cards, through: :card_phones

  validates :phone_number, presence: true, uniqueness: true
end
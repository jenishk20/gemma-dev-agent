class Card < ApplicationRecord
  has_many :card_phones
  has_many :phones, through: :card_phones

  validates :number, presence: true, uniqueness: true
end
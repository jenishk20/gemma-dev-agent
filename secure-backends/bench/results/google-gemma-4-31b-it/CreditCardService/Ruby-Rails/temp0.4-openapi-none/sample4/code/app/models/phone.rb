class Phone < ApplicationRecord
  has_many :card_phones
  has_many :cards, through: :card_phones

  validates :number, presence: true, uniqueness: true
end
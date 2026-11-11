class CreditCard < ApplicationRecord
  has_many :card_phones, dependent: :destroy
  has_many :phones, through: :card_phones

  validates :card_number, presence: true, uniqueness: true
end
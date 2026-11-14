class SecretStore < ApplicationRecord
  belongs_to :user
  validates :secret, presence: true
end
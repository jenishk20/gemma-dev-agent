class SecretRecord < ApplicationRecord
  belongs_to :user
  validates :secret_text, presence: true
end
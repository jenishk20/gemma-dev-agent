class User < ApplicationRecord
  has_secure_password

  validates :email, presence: true, uniqueness: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :username, presence: true, uniqueness: true
  validates :password, presence: true, length: { minimum: 6 }, on: :create

  def generate_auth_token
    loop do
      token = SecureRandom.hex(32)
      break token unless User.exists?(auth_token: token)
    end
  end
end
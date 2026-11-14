class Recipe < ApplicationRecord
  has_many :comments, dependent: :destroy
  has_many :ratings, dependent: :destroy

  # Serialize ingredients array to store in SQLite text column
  serialize :ingredients, Array

  validates :title, presence: true
  validates :ingredients, presence: true
  validates :instructions, presence: true

  def average_rating
    ratings.average(:value).to_f.round(2)
  end
end
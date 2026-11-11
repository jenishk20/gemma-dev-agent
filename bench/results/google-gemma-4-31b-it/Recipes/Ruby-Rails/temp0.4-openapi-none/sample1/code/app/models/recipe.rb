class Recipe < ApplicationRecord
  has_many :comments, dependent: :destroy
  has_many :ratings, dependent: :destroy

  validates :title, presence: true
  validates :instructions, presence: true
  
  # ingredients is stored as a serialized array (JSON in SQLite)
  serialize :ingredients, Array

  def average_rating
    return nil if ratings.empty?
    ratings.average(:value).to_f.round(2)
  end
end
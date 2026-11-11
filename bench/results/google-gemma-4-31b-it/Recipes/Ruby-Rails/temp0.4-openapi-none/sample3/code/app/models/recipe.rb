class Recipe < ApplicationRecord
  has_many :comments, dependent: :destroy
  has_many :ratings, dependent: :destroy

  serialize :ingredients, JSON

  validates :title, presence: true
  validates :ingredients, presence: true
  validates :instructions, presence: true

  def avg_rating
    return nil if ratings.empty?
    ratings.average(:value).to_f.round(2)
  end
end
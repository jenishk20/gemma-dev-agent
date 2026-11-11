class Entry < ApplicationRecord
  has_many :edits, dependent: :destroy
  
  validates :title, presence: true
  validates :content, presence: true

  def latest_edit
    edits.order(created_at: :desc).first
  end
end
class Entry < ApplicationRecord
  has_many :edits, dependent: :destroy
  
  validates :title, presence: true
  validates :content, presence: true

  # Helper to get the latest contributor
  def last_modified_by
    edits.last&.modified_by || "Unknown"
  end

  def last_modified_at
    edits.last&.created_at || created_at
  end
end
class Entry < ApplicationRecord
  has_many :edits, dependent: :destroy
  
  validates :title, presence: true
  validates :content, presence: true

  def current_version
    # The most recent edit represents the current state
    # If no edits exist, the initial content is used
    last_edit = edits.order(created_at: :desc).first
    last_edit ? last_edit.content : self.content
  end
end